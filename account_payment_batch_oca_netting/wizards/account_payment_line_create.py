# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.osv import expression


class AccountPaymentLineCreate(models.TransientModel):
    _inherit = "account.payment.line.create"

    netting = fields.Boolean(related="order_id.payment_method_line_id.netting")
    include_receivables = fields.Boolean(
        default=True,
        help="Also propose the receivables of the partners that have a payable "
        "in the order or in the selection, to net them.",
    )

    @api.depends("include_receivables")
    def _compute_eligible_move_line_ids(self):
        return super()._compute_eligible_move_line_ids()

    def _prepare_move_line_domain(self):
        domain = super()._prepare_move_line_domain()
        if not (self.netting and self.include_receivables):
            return domain
        payable_partners = (
            self.order_id.payment_line_ids.filtered(
                lambda line: line.amount_currency > 0
            ).partner_id
            | self.env["account.move.line"].search(domain).partner_id
        )
        return expression.OR(
            [domain, self._prepare_receivable_domain(payable_partners)]
        )

    def _prepare_receivable_domain(self, payable_partners):
        domain = [
            ("reconciled", "=", False),
            ("company_id", "=", self.order_id.company_id.id),
            ("move_id.payment_state", "in", ("not_paid", "partial")),
            ("partner_id", "in", payable_partners.ids),
            ("account_id.reconcile", "=", True),
            ("account_id", "not in", self.order_id._get_liquidity_accounts().ids),
            ("debit", ">", 0),
            ("payment_id", "=", False),
            ("statement_line_id", "=", False),
        ]
        if self.target_move == "posted":
            domain.append(("move_id.state", "=", "posted"))
        else:
            domain.append(("move_id.state", "in", ("draft", "posted")))
        if self.partner_ids:
            domain.append(("partner_id", "in", self.partner_ids.ids))
        if self.date_type == "due":
            domain += [
                "|",
                ("date_maturity", "<=", self.due_date),
                ("date_maturity", "=", False),
            ]
        elif self.date_type == "move":
            domain.append(("date", "<=", self.move_date))
        if self.invoice:
            domain.append(
                (
                    "move_id.move_type",
                    "in",
                    ("in_invoice", "out_invoice", "in_refund", "out_refund"),
                )
            )
        paylines = self.env["account.payment.line"].search(
            [
                ("state", "in", ("draft", "open", "generated")),
                ("move_line_id", "!=", False),
            ]
        )
        if paylines:
            domain.append(("id", "not in", paylines.move_line_id.ids))
        return domain
