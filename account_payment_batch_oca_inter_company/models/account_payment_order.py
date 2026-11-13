# Copyright 2022 Akretion France (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def generated2uploaded(self):
        res = super().generated2uploaded()
        self.payment_ids._reconcile_inter_company_invoices()
        return res
