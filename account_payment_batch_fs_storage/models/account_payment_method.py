# Copyright 2024 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountPaymentMethod(models.Model):
    _inherit = "account.payment.method"

    storage = fields.Selection(
        selection="_get_selection_storage",
        default="",
        company_dependent=True,
        help="Storage where to put the file after generation",
    )

    def _get_selection_storage(self):
        """
        This is to avoid giving access to the model fs.storage
        at groups other than base.group_system
        """
        if self.env.company.fs_storage_source_payment == "method":
            storages = self.env.company.sudo().fs_storage_ids
            return [(str(r.id), r.display_name) for r in storages]
        return []
