# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import NettingCommon


@freeze_time("2026-01-15 12:00:00")
@tagged("-at_install", "post_install")
class TestNetZero(NettingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_partner = cls.env["res.partner"].create({"name": "Other Partner"})
        cls.env["res.partner.bank"].create(
            {
                "acc_number": "FR7600004",
                "partner_id": cls.other_partner.id,
                "allow_out_payment": True,
            }
        )
        cls.invoice = cls._create_invoice("in_invoice", 500)
        cls.customer_invoice = cls._create_invoice("out_invoice", 500)
        cls.other_invoice = cls._create_invoice(
            "in_invoice", 200, partner=cls.other_partner
        )

    def _create_net_zero_order(self):
        return self._create_order(
            self._open_line(self.invoice)
            | self._open_line(self.customer_invoice)
            | self._open_line(self.other_invoice)
        )

    def test_net_zero_group_confirmed_without_payment(self):
        order = self._confirm(self._create_net_zero_order())
        self.assertRecordValues(
            order.payment_ids, [{"partner_id": self.other_partner.id, "amount": 200}]
        )
        self.assertEqual(order.payment_lot_ids.payment_ids, order.payment_ids)
        self.assertFalse(order.netting_move_ids)

    def _create_order_without_bank(self, payable_amount, receivable_amount):
        partner = self.env["res.partner"].create({"name": "Partner Without Bank"})
        invoice = self._create_invoice("in_invoice", payable_amount, partner=partner)
        customer_invoice = self._create_invoice(
            "out_invoice", receivable_amount, partner=partner
        )
        return self._create_order(
            self._open_line(invoice) | self._open_line(customer_invoice)
        )

    def test_net_zero_group_without_bank_account(self):
        order = self._upload(self._create_order_without_bank(500, 500))
        self.assertFalse(order.payment_ids)
        self.assertRecordValues(order.netting_move_ids, [{"state": "posted"}])

    def test_positive_group_without_bank_account_refused(self):
        order = self._create_order_without_bank(500, 200)
        with self.assertRaisesRegex(UserError, "Missing Partner Bank Account"):
            self._confirm(order)

    def test_open_netting_moves(self):
        order = self._upload(self._create_net_zero_order())
        self.assertEqual(order.netting_move_count, 1)
        self.assertEqual(
            order.action_open_netting_moves()["res_id"], order.netting_move_ids.id
        )

    def test_net_zero_move_posted_at_upload(self):
        order = self._upload(self._create_net_zero_order())
        move = order.netting_move_ids
        self.assertRecordValues(
            move,
            [
                {
                    "move_type": "entry",
                    "state": "posted",
                    "journal_id": order.journal_id.id,
                    "date": order.payment_line_ids[0].date,
                    "ref": order.name,
                }
            ],
        )
        self.assertRecordValues(
            move.line_ids.sorted("balance"),
            [
                {
                    "account_id": self.receivable_account.id,
                    "partner_id": self.partner.id,
                    "balance": -500,
                    "reconciled": True,
                },
                {
                    "account_id": self.payable_account.id,
                    "partner_id": self.partner.id,
                    "balance": 500,
                    "reconciled": True,
                },
            ],
        )
        self.assertRecordValues(
            self.invoice | self.customer_invoice | self.other_invoice,
            [{"amount_residual": 0}, {"amount_residual": 0}, {"amount_residual": 0}],
        )

    def test_zero_group_without_receivable_refused(self):
        order = self._create_order(self._open_line(self.invoice))
        order.payment_line_ids.amount_currency = 0
        with self.assertRaisesRegex(UserError, "negative or null"):
            self._confirm(order)

    def test_net_zero_cancel_and_redo(self):
        order = self._upload(self._create_net_zero_order())
        move = order.netting_move_ids
        order.action_cancel()
        self.assertEqual(move.state, "cancel")
        self.assertRecordValues(
            self.invoice | self.customer_invoice,
            [{"amount_residual": 500}, {"amount_residual": 500}],
        )
        order.cancel2draft()
        self._upload(order)
        self.assertRecordValues(order.netting_move_ids, [{"state": "posted"}])
        self.assertRecordValues(
            self.invoice | self.customer_invoice,
            [{"amount_residual": 0}, {"amount_residual": 0}],
        )

    def test_net_zero_foreign_currency_rounding(self):
        invoice = self._create_invoice(
            "in_invoice", 10.01, currency=self.other_currency
        )
        other_invoice = self._create_invoice(
            "in_invoice", 12.01, currency=self.other_currency
        )
        customer_invoice = self._create_invoice(
            "out_invoice", 22.02, currency=self.other_currency
        )
        order = self._create_order(
            self._open_line(invoice)
            | self._open_line(other_invoice)
            | self._open_line(customer_invoice)
        )
        self._upload(order)
        self.assertFalse(order.payment_ids)
        self.assertEqual(order.netting_move_ids.state, "posted")
        self.assertRecordValues(
            invoice | other_invoice | customer_invoice,
            [{"amount_residual": 0}, {"amount_residual": 0}, {"amount_residual": 0}],
        )
