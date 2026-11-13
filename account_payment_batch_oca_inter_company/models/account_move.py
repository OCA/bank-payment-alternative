# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_installment_lines(self):
        return self.line_ids.filtered(
            lambda line: line.display_type == "payment_term"
        ).sorted(lambda line: (line.date_maturity or date.min, line.id))
