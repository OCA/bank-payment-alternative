# Copyright (c) 2025 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.depends("pos_payment_method_id", "force_outstanding_account_id")
    def _compute_outstanding_account_id(self):
        res = super()._compute_outstanding_account_id()
        for pay in self:
            if pay.pos_payment_method_id and pay.force_outstanding_account_id:
                pay.outstanding_account_id = pay.force_outstanding_account_id
        return res
