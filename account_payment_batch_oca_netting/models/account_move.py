# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    netting_payment_order_id = fields.Many2one(
        comodel_name="account.payment.order",
        readonly=True,
        copy=False,
        index="btree_not_null",
        help="Payment order whose net-zero transfer group this entry books.",
    )
