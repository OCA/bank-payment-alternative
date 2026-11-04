# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountPaymentLine(models.Model):
    _inherit = "account.payment.line"

    def _is_dividend_payment_line(self):
        self.ensure_one()
        receivable_account = self.company_id.interco_dividend_receivable_account_id
        return (
            bool(receivable_account)
            and self.move_line_id.account_id == receivable_account
        )

    def _get_dividend_dest_line(self, dest_company, mirrored_payment_lines):
        self.ensure_one()
        account = dest_company._get_interco_dividend_payable_account()
        currency = dest_company.currency_id
        expected_residual = -self._get_mirror_sign() * self.amount_currency
        same_amount_dividends = mirrored_payment_lines.filtered(
            lambda payment_line: payment_line._is_dividend_payment_line()
            and currency.is_zero(payment_line.amount_currency - self.amount_currency)
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

    def _get_dest_line_by_payment_line(self, dest_company):
        dest_line_by_payment_line = super()._get_dest_line_by_payment_line(dest_company)
        for payment_line in self.filtered(
            lambda payment_line: payment_line._is_dividend_payment_line()
        ):
            dest_line_by_payment_line[payment_line] = (
                payment_line._get_dividend_dest_line(dest_company, self)
            )
        return dest_line_by_payment_line

    def _prepare_mirror_move_line(self, dest_line, dest_company):
        vals = super()._prepare_mirror_move_line(dest_line, dest_company)
        if self._is_dividend_payment_line():
            account = dest_company._get_interco_dividend_payable_account()
            vals.update(
                {
                    "partner_id": self.company_id.partner_id.id,
                    "account_id": account.id,
                }
            )
        return vals

    def _prepare_net_zero_mirror_move_vals(self, netting_move, dest_company):
        return {
            "move_type": "entry",
            "journal_id": dest_company._get_interco_netting_journal().id,
            "company_id": dest_company.id,
            "date": netting_move.date,
            "ref": netting_move.ref,
        }

    def _create_net_zero_mirror_move(self, netting_move):
        dest_company = self._get_inter_company()
        if not dest_company:
            return self.env["account.move"].browse()
        return (
            self.sudo()
            .with_company(dest_company)
            ._create_mirror_move(
                dest_company,
                self._prepare_net_zero_mirror_move_vals(netting_move, dest_company),
            )
        )
