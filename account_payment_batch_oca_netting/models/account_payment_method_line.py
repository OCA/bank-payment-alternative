# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    netting = fields.Boolean(
        help="Allow receivables as negative lines of outbound payment orders: "
        "each transfer pays the net amount of its lines.",
    )
