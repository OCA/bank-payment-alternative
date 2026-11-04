# Copyright 2022 Akretion France (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, _, models


class AccountPaymentLine(models.Model):
    _inherit = "account.payment.line"

    def _get_inter_company(self):
        return (
            self.env["res.company"]
            .sudo()
            .search(
                [
                    (
                        "partner_id",
                        "=",
                        self.partner_id.ensure_one().commercial_partner_id.id,
                    ),
                    ("id", "!=", self.company_id.ensure_one().id),
                ],
                limit=1,
            )
        )

    def _get_mirror_sign(self):
        return -1 if self.order_id.ensure_one().payment_type == "outbound" else 1

    def _prepare_mirror_move_line(self, dest_line, dest_company):
        self.ensure_one()
        balance = self._get_mirror_sign() * self.amount_currency
        if dest_line:
            dest_invoice = dest_line.move_id
            partner = dest_invoice.commercial_partner_id
            account = dest_line.account_id
            if dest_invoice.state == "draft":
                name = dest_invoice.ref
            else:
                name = dest_invoice.name
        else:
            partner = self.company_id.partner_id.with_company(dest_company)
            name = self.communication
            if balance < 0:
                account = partner.property_account_receivable_id
            else:
                account = partner.property_account_payable_id
        return {
            "partner_id": partner.id,
            "name": name,
            "account_id": account.id,
            "balance": balance,
        }

    def _get_dest_invoice(self, dest_company):
        self.ensure_one()
        orig_invoice = self.move_line_id.move_id
        if orig_invoice.auto_generated:
            return orig_invoice.auto_invoice_id
        return self.env["account.move"].search(
            [
                ("auto_invoice_id", "=", orig_invoice.id),
                ("company_id", "=", dest_company.id),
            ],
            limit=1,
        )

    def _get_dest_line_by_payment_line(self, dest_company):
        return {
            payment_line: payment_line._get_dest_invoice(
                dest_company
            ).line_ids.filtered(
                lambda line: line.account_id.account_type
                in ("asset_receivable", "liability_payable")
            )[:1]
            for payment_line in self
        }

    def _create_mirror_move(self, dest_company, move_vals, extra_line_vals_list=()):
        dest_line_by_payment_line = self._get_dest_line_by_payment_line(dest_company)
        line_vals_list = [
            payment_line._prepare_mirror_move_line(dest_line, dest_company)
            for payment_line, dest_line in dest_line_by_payment_line.items()
        ] + list(extra_line_vals_list)
        move = self.env["account.move"].create(
            {
                **move_vals,
                "line_ids": [Command.create(vals) for vals in line_vals_list],
            }
        )
        move.action_post()
        mirror_lines = move.line_ids.sorted("id")[: len(self)]
        for mirror_line, dest_line in zip(
            mirror_lines, dest_line_by_payment_line.values(), strict=True
        ):
            if dest_line.move_id.state == "posted":
                (mirror_line | dest_line).reconcile()
        self.filtered(
            lambda payment_line: dest_line_by_payment_line[payment_line].move_id.state
            != "posted"
        )._notify_unreconciled_payment_lines(move)
        return move

    def _notify_unreconciled_payment_lines(self, move):
        if not self:
            return
        self.order_id.message_post(
            body=_(
                "Inter-company entry %(move)s of the company %(company_name)s:"
                " no single posted linked entry found for %(communications)s."
                " Left unreconciled.",
                move=move.name,
                company_name=move.company_id.name,
                communications=", ".join(self.mapped("communication")),
            )
        )
