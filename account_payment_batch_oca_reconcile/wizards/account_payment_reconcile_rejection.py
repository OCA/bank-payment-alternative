# Copyright 2026 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount, format_date

logger = logging.getLogger(__name__)


class AccountPaymentReconcileRejection(models.TransientModel):
    _name = "account.payment.reconcile.rejection"
    _description = "Account Payment Reconcile Rejection"

    statement_line_id = fields.Many2one(
        "account.bank.statement.line", readonly=True, required=True
    )
    statement_line_date = fields.Date(related="statement_line_id.date")
    statement_line_currency_id = fields.Many2one(
        related="statement_line_id.currency_id"
    )
    statement_line_rejected_payment_min_date = fields.Date(
        related="statement_line_id.rejected_payment_min_date"
    )
    statement_line_rejected_payment_min_amount = fields.Monetary(
        related="statement_line_id.rejected_payment_min_amount",
        currency_field="statement_line_currency_id",
    )
    statement_line_rejected_payment_max_amount = fields.Monetary(
        related="statement_line_id.rejected_payment_max_amount",
        currency_field="statement_line_currency_id",
    )
    statement_line_payment_ref = fields.Char(related="statement_line_id.payment_ref")
    statement_line_journal_id = fields.Many2one(related="statement_line_id.journal_id")
    statement_line_amount = fields.Monetary(
        related="statement_line_id.amount", currency_field="statement_line_currency_id"
    )
    company_id = fields.Many2one(related="statement_line_id.company_id")
    payment_type = fields.Selection(
        [
            ("inbound", "Inbound"),
            ("outbound", "Outbound"),
        ],
        compute="_compute_payment_id",
        store=True,
        precompute=True,
        help="Payment type of the origin payment",
    )
    match_method = fields.Selection(
        [
            ("endtoend_id", "End to end ID"),
            ("remittance_info", "Communication"),
            ("partner_last", "Last payment of partner with that amount"),
            ("no_partner_no_match", "No payment found. Select a partner manually."),
            ("partner_no_match", "No payment found."),
        ],
        compute="_compute_payment_id",
        store=True,
        precompute=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        compute="_compute_payment_id",
        store=True,
        precompute=True,
        readonly=False,
        domain=[("parent_id", "=", False)],
    )
    payment_id = fields.Many2one(
        "account.payment",
        compute="_compute_payment_id",
        store=True,
        readonly=False,
        precompute=True,
        domain="[('company_id', '=', company_id), "
        "('journal_id', '=', statement_line_journal_id), "
        "('partner_id', '=', partner_id), "
        "('currency_id', '=', statement_line_currency_id), "
        "('payment_type', '=', payment_type), "
        "('state', 'in', ('paid', 'in_process')), "
        "('is_matched', '=', True), "
        "('payment_order_id', '!=', False), "
        "('date', '<=', statement_line_date), "
        "('date', '>=', statement_line_rejected_payment_min_date), "
        "('amount', '<=', statement_line_rejected_payment_max_amount), "
        "('amount', '>=', statement_line_rejected_payment_min_amount), "
        "('memo', '!=', False), "
        "('payment_reference', '!=', False)]",
        required=True,
        string="Origin Payment",
    )
    payment_memo = fields.Char(related="payment_id.memo", string="Origin Payment Memo")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        assert self.env.context.get("active_model") == "account.bank.statement.line"
        statement_line_id = self.env.context.get("active_id")
        res["statement_line_id"] = statement_line_id
        return res

    @api.depends("statement_line_id", "partner_id")
    def _compute_payment_id(self):
        for wiz in self:
            payment_type = payment_id = partner_id = match_method = False
            if wiz.statement_line_id:
                payment_type, payment_id, partner_id, match_method = (
                    wiz.statement_line_id._get_rejection_info()
                )
            wiz.payment_type = payment_type
            wiz.payment_id = payment_id
            wiz.partner_id = partner_id
            wiz.match_method = match_method

    def run(self):
        self.ensure_one()
        if not self.payment_id:
            raise UserError(self.env._("The Origin Payment is not set."))
        payment = self.payment_id
        st_line = self.statement_line_id
        assert self.payment_type
        sign = self.payment_type == "outbound" and 1 or -1
        if payment.currency_id != st_line.currency_id:
            raise UserError(
                self.env._(
                    "The currency of the payment (%(cur_payment)s) is different from "
                    "the currency of the bank statement line (%(st_line_currency)s).",
                    cur_payment=payment.currency_id.name,
                    st_line_currency=st_line.currency_id.name,
                )
            )
        if payment.currency_id.compare_amounts(payment.amount, st_line.amount * sign):
            raise UserError(
                self.env._(
                    "The amount of the rejection (%(rej_amount)s) is different from "
                    "the amount of the payment (%(pay_amount)s).",
                    rej_amount=format_amount(
                        self.env, st_line.amount * sign, st_line.currency_id
                    ),
                    pay_amount=format_amount(
                        self.env, payment.amount, payment.currency_id
                    ),
                )
            )
        payment.action_reject()  # only write 'reject' on 'state' field
        msg = self.env._(
            "Payment <a href=# data-oe-model=account.payment "
            "data-oe-id=%(pay_id)s>%(pay_name)s</a> "
            "rejected on %(date)s.",
            pay_id=payment.id,
            pay_name=payment.display_name,
            date=format_date(self.env, st_line.date),
        )
        for invoice in payment.invoice_ids:
            invoice.message_post(body=Markup(msg))
        if payment.payment_order_id:
            payment.payment_order_id.message_post(
                body=Markup(
                    self.env._(
                        "Payment <a href=# data-oe-model=account.payment "
                        "data-oe-id=%(pay_id)s>%(pay_name)s</a> of "
                        "<strong>%(partner)s</strong> amount %(amount)s rejected.",
                        pay_id=payment.id,
                        pay_name=payment.display_name,
                        partner=payment.partner_id.display_name,
                        amount=format_amount(
                            self.env, payment.amount, payment.currency_id
                        ),
                    )
                )
            )
        destination_account = payment.destination_account_id
        if payment.move_id:
            logger.info(
                "Payment %s ID %s has an underlying journal entry",
                payment.display_name,
                payment.id,
            )
            future_reject_counterpart_mline = payment.move_id.line_ids.filtered(
                lambda x: x.account_id and x.account_id == destination_account
            )
        else:
            logger.info(
                "Payment %s ID %d has no underlying journal entry",
                payment.display_name,
                payment.id,
            )
            if not payment.invoice_ids:
                raise UserError(
                    self.env._(
                        "Payment '%s' is not linked to an invoice.",
                        payment.display_name,
                    )
                )
            destination_move_lines = payment.invoice_ids.line_ids.filtered(
                lambda x: x.account_id and x.account_id == destination_account
            )
            future_reject_counterpart_mline = (
                destination_move_lines.full_reconcile_id.reconciled_line_ids.filtered(
                    lambda x: x.journal_id.type in ("bank", "cash")
                )
            )

        if not future_reject_counterpart_mline:
            raise UserError(
                self.env._(
                    "Failed to identify the journal item to unreconcile and "
                    "set as counterpart of this bank statement line."
                )
            )
        # Unreconcile
        future_reject_counterpart_mline.remove_move_reconcile()
        # Set counterpart
        new_data = []
        for line in st_line.reconcile_data_info["data"]:
            new_data.append(line)
        for line in future_reject_counterpart_mline:
            reconcile_auxiliary_id, lines = st_line._get_reconcile_line(
                line, "other", True, 0.0
            )
            new_data += lines
        data_info = st_line._recompute_suspense_line(
            new_data,
            st_line.reconcile_data_info["reconcile_auxiliary_id"],
            st_line.manual_reference,
        )
        st_line.reconcile_data_info = data_info
        # button "Validate"
        st_line.reconcile_bank_line()
