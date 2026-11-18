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

    def _prepare_move_line_default_vals(
        self, write_off_line_vals=None, force_balance=None
    ):
        if self._is_netting() and force_balance is None:
            force_balance = sum(
                vals["balance"] for vals in self._prepare_move_counterpart_lines({})
            )
        return super()._prepare_move_line_default_vals(
            write_off_line_vals=write_off_line_vals, force_balance=force_balance
        )

    def _prepare_move_counterpart_lines(self, default_values):
        if not self._is_netting():
            return super()._prepare_move_counterpart_lines(default_values)
        return [
            payline._prepare_netting_move_line_vals(
                self.date, self.destination_account_id
            )
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
        self.payment_line_ids._reconcile_netting_counterparts(counterpart_lines)
