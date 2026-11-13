# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = "res.company"

    interco_dividend_receivable_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Interco Dividend Receivable Account",
        check_company=True,
        domain="[('deprecated', '=', False), ('reconcile', '=', True)]",
        help="A netted payment line on this account is a dividend due by the "
        "company receiving the transfer.",
    )
    interco_dividend_payable_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Interco Dividend Payable Account",
        check_company=True,
        domain="[('deprecated', '=', False), ('reconcile', '=', True)]",
        help="Account of the inter-company entry line mirroring a dividend netted "
        "by the paying company.",
    )
    interco_netting_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Interco Netting Journal",
        check_company=True,
        domain="[('type', '=', 'general')]",
        help="Journal of the inter-company entry mirroring a net-zero transfer group "
        "of the paying company.",
    )

    def _get_interco_dividend_payable_account(self):
        self.ensure_one()
        if not self.interco_dividend_payable_account_id:
            raise UserError(
                _(
                    "The inter-company dividend payable account is not set"
                    " on the company %(company_name)s.",
                    company_name=self.name,
                )
            )
        return self.interco_dividend_payable_account_id

    def _get_interco_netting_journal(self):
        self.ensure_one()
        if not self.interco_netting_journal_id:
            raise UserError(
                _(
                    "The inter-company netting journal is not set"
                    " on the company %(company_name)s.",
                    company_name=self.name,
                )
            )
        return self.interco_netting_journal_id
