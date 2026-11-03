# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _is_netting(self):
        self.ensure_one()
        return bool(
            self.payment_order_id.payment_method_line_id.netting
            and self.payment_line_ids
        )

    def _prepare_move_counterpart_lines(self, default_values):
        if not self._is_netting():
            return super()._prepare_move_counterpart_lines(default_values)
        company = self.company_id
        return [
            {
                "name": payline.communication,
                "date_maturity": self.date,
                "partner_id": self.partner_id.id,
                "account_id": (
                    payline.move_line_id.account_id or self.destination_account_id
                ).id,
                "currency_id": self.currency_id.id,
                "amount_currency": payline.amount_currency,
                "balance": self.currency_id._convert(
                    payline.amount_currency, company.currency_id, company, self.date
                ),
            }
            for payline in self.payment_line_ids
        ]

    def _synchronize_to_moves(self, changed_fields):
        payments = self.filtered(lambda pay: not pay._is_netting())
        return super(AccountPayment, payments)._synchronize_to_moves(changed_fields)

    def _reconcile_payment_lines(self):
        if not self._is_netting():
            return super()._reconcile_payment_lines()
        if not self.move_id:
            return
        counterpart_lines = self.move_id.line_ids.filtered(
            lambda line: line.account_id not in self._get_valid_liquidity_accounts()
        )
        for payline in self.payment_line_ids.filtered("move_line_id"):
            counterpart = counterpart_lines.filtered(
                lambda line, payline=payline: line.account_id
                == payline.move_line_id.account_id
                and self.currency_id.compare_amounts(
                    line.amount_currency, payline.amount_currency
                )
                == 0
            )[:1]
            counterpart_lines -= counterpart
            (counterpart | payline.move_line_id).reconcile()
