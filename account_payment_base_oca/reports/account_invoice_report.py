# Copyright 2024-2025 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.tools import SQL


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    payment_method_line_id = fields.Many2one(
        "account.payment.method.line", readonly=True, string="Payment Method"
    )

    def _select_list(self, table):
        res = super()._select_list(table)
        res.append(
            SQL(
                "%s AS payment_method_line_id",
                table.move_id.preferred_payment_method_line_id,
            )
        )
        return res
