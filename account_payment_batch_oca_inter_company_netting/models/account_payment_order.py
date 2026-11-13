# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def _create_netting_moves(self):
        paylines_by_move = super()._create_netting_moves()
        for move, paylines in paylines_by_move.items():
            move.netting_auto_move_id = paylines._create_net_zero_mirror_move(move)
        return paylines_by_move
