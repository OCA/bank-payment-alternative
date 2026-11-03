# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPaymentLine(models.Model):
    _inherit = "account.payment.line"

    def _compute_partner_bank_id(self):
        res = super()._compute_partner_bank_id()
        for line in self:
            order = line.order_id
            if (
                order.payment_method_line_id.netting
                and order.payment_method_id.bank_account_required
                and line.move_line_id.move_id.move_type == "in_refund"
                and line.partner_bank_id.partner_id != line.partner_id
            ):
                line.partner_bank_id = line.partner_id.bank_ids[:1]
        return res

    @api.constrains("amount_currency", "move_line_id", "order_id")
    def _check_netting_line(self):
        for line in self:
            currency = line.currency_id
            if not (
                line.order_id.payment_method_line_id.netting
                and currency.compare_amounts(line.amount_currency, 0) < 0
            ):
                continue
            move_line = line.move_line_id
            if not move_line or move_line.balance <= 0:
                raise ValidationError(
                    _(
                        "Payment line %(name)s is negative: it must be linked "
                        "to a debit journal item.",
                        name=line.name,
                    )
                )
            if (
                currency.compare_amounts(
                    -line.amount_currency, move_line.amount_residual_currency
                )
                > 0
            ):
                raise ValidationError(
                    _(
                        "On payment line %(name)s, the netted amount "
                        "%(amount).2f exceeds the residual %(residual).2f "
                        "of journal item %(move_line)s.",
                        name=line.name,
                        amount=-line.amount_currency,
                        residual=move_line.amount_residual_currency,
                        move_line=move_line.display_name,
                    )
                )

    def _payment_line_grouping_account_key(self):
        if self.order_id.payment_method_line_id.netting:
            return False
        return super()._payment_line_grouping_account_key()

    def _prepare_write_draft2open(self):
        vals = super()._prepare_write_draft2open()
        order = self.order_id
        if order.payment_method_line_id.netting:
            today = fields.Date.context_today(self)
            order_date = (
                order.date_prefered == "fixed" and order.date_scheduled or today
            )
            vals["date"] = max(today, order_date)
        return vals

    def _draft2open_payment_line_check(self):
        errors = super()._draft2open_payment_line_check()
        if (
            self.order_id.payment_method_line_id.netting
            and self.communication_type != "free"
            and self.currency_id.compare_amounts(self.amount_currency, 0) < 0
        ):
            errors.append(
                _(
                    "Payment line %(name)s has a structured reference: "
                    "it can't be netted.",
                    name=self.name,
                )
            )
        return errors

    def _prepare_account_payment_vals(self, payment_lot, pay_sequence):
        if not self.order_id.payment_method_line_id.netting:
            return super()._prepare_account_payment_vals(payment_lot, pay_sequence)
        paylines = self.sorted("amount_currency", reverse=True)
        vals = super(AccountPaymentLine, paylines[:1])._prepare_account_payment_vals(
            payment_lot, pay_sequence
        )
        vals.update(
            {
                "amount": sum(paylines.mapped("amount_currency")),
                "payment_reference": " - ".join(paylines.mapped("communication")),
                "payment_line_ids": [Command.set(paylines.ids)],
                "invoice_ids": [Command.set(paylines.move_line_id.move_id.ids)],
            }
        )
        return vals
