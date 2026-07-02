# Copyright 2024 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    storage = fields.Selection(
        selection="_get_selection_storage",
        company_dependent=True,
        help="Storage where to put the file after generation",
    )

    def _get_selection_storage(self):
        if self.env.company.fs_storage_source_payment == "method_line":
            storages = self.env.company.fs_storage_ids
            return [(str(r.id), r.display_name) for r in storages]
        return []
