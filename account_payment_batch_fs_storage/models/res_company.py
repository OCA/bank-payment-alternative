# Copyright 2024 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):

    _inherit = "res.company"

    fs_storage_source_payment = fields.Selection(
        string="fs storage source payment",
        selection=[
            ("method_line", "Payment Method Line"),
            ("method", "Payment Method"),
        ],
        default="method_line",
    )
