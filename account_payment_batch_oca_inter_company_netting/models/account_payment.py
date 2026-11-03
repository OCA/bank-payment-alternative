# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _is_dividend_payment_line(self, payment_line):
        self.ensure_one()
        receivable_account = self.company_id.interco_dividend_receivable_account_id
        return (
            bool(receivable_account)
            and payment_line.move_line_id.account_id == receivable_account
        )

    def _get_dividend_payable_account(self, dest_company):
        self.ensure_one()
        account = dest_company.interco_dividend_payable_account_id
        if not account:
            raise UserError(
                _(
                    "The inter-company dividend payable account is not set"
                    " on the company %(company_name)s.",
                    company_name=dest_company.name,
                )
            )
        return account

    def _get_dividend_dest_line(self, payment_line, dest_company):
        self.ensure_one()
        account = self._get_dividend_payable_account(dest_company)
        currency = dest_company.currency_id
        expected_residual = -self._get_mirror_sign() * payment_line.amount_currency
        same_amount_dividends = self.payment_line_ids.filtered(
            lambda line: self._is_dividend_payment_line(line)
            and currency.is_zero(line.amount_currency - payment_line.amount_currency)
        )
        if len(same_amount_dividends) > 1:
            return self.env["account.move.line"].browse()
        candidates = (
            self.env["account.move.line"]
            .search(
                [
                    ("company_id", "=", dest_company.id),
                    ("account_id", "=", account.id),
                    ("parent_state", "=", "posted"),
                    ("reconciled", "=", False),
                    ("partner_id", "in", [self.company_id.partner_id.id, False]),
                ]
            )
            .filtered(
                lambda line: currency.is_zero(line.amount_residual - expected_residual)
            )
        )
        return candidates if len(candidates) == 1 else candidates.browse()

    def _get_dest_line(self, payment_line, dest_company):
        dest_line = super()._get_dest_line(payment_line, dest_company)
        if self._is_dividend_payment_line(payment_line):
            return self._get_dividend_dest_line(payment_line, dest_company)
        return dest_line

    def _prepare_mirror_move_line(self, payment_line, dest_line, dest_company):
        vals = super()._prepare_mirror_move_line(payment_line, dest_line, dest_company)
        if self._is_dividend_payment_line(payment_line):
            vals.update(
                {
                    "partner_id": self.company_id.partner_id.id,
                    "account_id": self._get_dividend_payable_account(dest_company).id,
                }
            )
        return vals
