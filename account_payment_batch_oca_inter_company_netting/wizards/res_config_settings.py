# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    interco_dividend_receivable_account_id = fields.Many2one(
        related="company_id.interco_dividend_receivable_account_id",
        readonly=False,
    )
    interco_dividend_payable_account_id = fields.Many2one(
        related="company_id.interco_dividend_payable_account_id",
        readonly=False,
    )
    interco_netting_journal_id = fields.Many2one(
        related="company_id.interco_netting_journal_id",
        readonly=False,
    )
