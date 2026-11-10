# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def _prepare_filename(self):
        filename = super()._prepare_filename()

        if sequence := self.payment_method_line_id.filename_sequence_id:
            filename = sequence.next_by_id()

        return filename
