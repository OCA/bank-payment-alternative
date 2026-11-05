# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountPaymentMethodLine(models.Model):
    _inherit = "account.payment.method.line"

    netting = fields.Boolean(
        help="Allow receivables as negative lines of outbound payment orders: "
        "each transfer pays the net amount of its lines.",
    )

    @api.constrains("netting", "payment_method_id")
    def _check_netting_outbound(self):
        for line in self:
            if line.netting and line.payment_method_id.payment_type != "outbound":
                raise ValidationError(
                    _(
                        "Payment method line %(name)s can't use netting: "
                        "it isn't an outbound payment method.",
                        name=line.name,
                    )
                )
