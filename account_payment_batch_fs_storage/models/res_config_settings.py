# Copyright 2024 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    fs_storage_source_payment = fields.Selection(
        string="fs storage source payment",
        related="company_id.fs_storage_source_payment",
        readonly=False,
    )

    fs_storage_ids = fields.Many2many(
        comodel_name="fs.storage",
        string="Fs Storage allowed",
        compute="_compute_fs_storage_ids",
        inverse="_inverse_fs_storage_ids",
    )

    @api.depends("company_id")
    def _compute_fs_storage_ids(self):
        for rec in self:
            rec.fs_storage_ids = rec.company_id.fs_storage_ids

    def _inverse_fs_storage_ids(self):
        for rec in self:
            rec.company_id.fs_storage_ids = rec.fs_storage_ids

    @api.constrains("fs_storage_ids")
    def _check_fs_storage_ids(self):
        fs_storage_source = self.fs_storage_source_payment
        model = (
            "account.payment.method.line"
            if fs_storage_source == "method_line"
            else "account.payment.method"
        )
        allowed_storage_ids = [str(s.id) for s in self.fs_storage_ids]
        domain = allowed_storage_ids + [False, ""]
        used_not_allowed = self.env[model].search([("storage", "not in", domain)])
        if used_not_allowed:
            raise UserError(
                self.env._(
                    "Storage is already used on at least "
                    "one payment %(payment_source)s",
                    payment_source=fs_storage_source,
                )
            )
