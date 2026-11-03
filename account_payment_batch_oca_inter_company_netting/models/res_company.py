# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


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
