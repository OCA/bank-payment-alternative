# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    filename_sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        help="Sequence used to generate the filename",
    )
