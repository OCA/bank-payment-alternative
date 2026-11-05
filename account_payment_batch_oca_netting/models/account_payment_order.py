# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    netting_move_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="netting_payment_order_id",
        string="Net-Zero Entries",
        readonly=True,
    )
    netting_move_count = fields.Integer(compute="_compute_netting_move_count")

    @api.depends("netting_move_ids")
    def _compute_netting_move_count(self):
        for order in self:
            order.netting_move_count = len(order.netting_move_ids)

    def cancel2draft(self):
        moves = self.netting_move_ids
        moves.filtered(lambda move: move.state != "draft").button_draft()
        moves.unlink()
        return super().cancel2draft()

    def action_cancel(self):
        res = super().action_cancel()
        moves = self.netting_move_ids.filtered(lambda move: move.state != "cancel")
        draft_moves = moves.filtered(lambda move: move.state == "draft")
        draft_moves.unlink()
        (moves - draft_moves).button_cancel()
        return res

    def action_open_netting_moves(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_journal_line"
        )
        if self.netting_move_count == 1:
            action.update(
                {
                    "view_mode": "form,list,kanban,activity",
                    "views": False,
                    "view_id": False,
                    "res_id": self.netting_move_ids.id,
                }
            )
        else:
            action["domain"] = [("id", "in", self.netting_move_ids.ids)]
        return action

    def _draft2open_payment_group_check(self, paydict):
        if not self.payment_method_line_id.netting:
            return super()._draft2open_payment_group_check(paydict)
        net_sign = paydict["currency"].compare_amounts(paydict["total"], 0)
        if net_sign < 0:
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
        if net_sign == 0 and any(
            paydict["currency"].compare_amounts(payline.amount_currency, 0) < 0
            for payline in paydict["paylines"]
        ):
            return
        return super()._draft2open_payment_group_check(paydict)

    def open2generated(self):
        self.ensure_one()
        if self.payment_method_line_id.netting and not self.payment_ids:
            self.write(
                {
                    "state": "generated",
                    "date_generated": fields.Date.context_today(self),
                }
            )
            return {}
        return super().open2generated()

    def generated2uploaded(self):
        self.payment_line_ids._check_netting_line()
        res = super().generated2uploaded()
        if self.payment_method_line_id.netting:
            self._create_netting_moves()
        return res

    def _get_liquidity_accounts(self):
        self.ensure_one()
        journal = self.journal_id
        return (
            journal.default_account_id
            | self.payment_method_line_id.payment_account_id
            | journal.inbound_payment_method_line_ids.payment_account_id
            | journal.outbound_payment_method_line_ids.payment_account_id
        )

    def _create_netting_moves(self):
        self.ensure_one()
        group_lines = self.payment_method_line_id.group_lines
        group_paylines = defaultdict(lambda: self.env["account.payment.line"])
        for payline in self.payment_line_ids - self.payment_ids.payment_line_ids:
            pay_key = (
                payline._payment_line_grouping_key() if group_lines else payline.id
            )
            group_paylines[pay_key] |= payline
        moves = self.env["account.move"].create(
            [
                paylines._prepare_netting_move_vals()
                for paylines in group_paylines.values()
            ]
        )
        moves.action_post()
        paylines_by_move = dict(zip(moves, group_paylines.values(), strict=True))
        for move, paylines in paylines_by_move.items():
            paylines._reconcile_netting_counterparts(move.line_ids)
        return paylines_by_move
