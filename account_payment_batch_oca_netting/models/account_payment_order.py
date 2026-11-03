# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def _draft2open_payment_group_check(self, paydict):
        if (
            self.payment_method_line_id.netting
            and paydict["currency"].compare_amounts(paydict["total"], 0) < 0
        ):
            payline = paydict["paylines"][0]
            raise UserError(
                _(
                    "The net amount for partner '%(partner)s' and bank account "
                    "'%(bank_account)s' is negative (%(amount).2f).",
                    partner=payline.partner_id.name,
                    bank_account=payline.partner_bank_id.display_name or "-",
                    amount=paydict["total"],
                )
            )
        return super()._draft2open_payment_group_check(paydict)
