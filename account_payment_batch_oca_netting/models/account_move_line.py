# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def create_payment_line_from_move_line(self, payment_order):
        if not payment_order.payment_method_line_id.netting:
            return super().create_payment_line_from_move_line(payment_order)
        supplier_invoice_lines = self.filtered(
            lambda line: line.move_id.move_type == "in_invoice"
        )
        return super(
            AccountMoveLine, supplier_invoice_lines
        ).create_payment_line_from_move_line(payment_order) | super(
            AccountMoveLine, self - supplier_invoice_lines
        ).create_payment_line_from_move_line(payment_order)
