# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    netting_auto_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Inter Company Netting Entry",
        readonly=True,
        copy=False,
    )

    def unlink(self):
        mirrors = self.sudo().netting_auto_move_id
        if mirrors:
            mirrors.with_context(force_delete=True).unlink()
        return super().unlink()

    def button_draft(self):
        res = super().button_draft()
        mirrors = self.sudo().netting_auto_move_id.filtered(
            lambda move: move.state == "posted"
        )
        if mirrors:
            mirrors.button_draft()
        return res

    def button_cancel(self):
        res = super().button_cancel()
        mirrors = self.sudo().netting_auto_move_id.filtered(
            lambda move: move.state in ("draft", "posted")
        )
        if mirrors:
            mirrors.button_cancel()
        return res
