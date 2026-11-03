# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import NettingCommon


@tagged("-at_install", "post_install")
class TestNetting(NettingCommon):
    def test_positive_group(self):
        invoice = self._create_invoice("in_invoice", 1000)
        customer_invoice = self._create_invoice("out_invoice", 300)
        order = self._create_order(
            self._open_line(invoice) | self._open_line(customer_invoice)
        )
        self._confirm(order)
        self.assertRecordValues(order.payment_ids, [{"amount": 700}])
        self._upload(order)
        payment = order.payment_ids
        self.assertRecordValues(
            payment.move_id.line_ids.sorted("balance"),
            [
                {"account_id": self.outstanding_account.id, "balance": -700},
                {"account_id": self.receivable_account.id, "balance": -300},
                {"account_id": self.payable_account.id, "balance": 1000},
            ],
        )
        self.assertRecordValues(
            self._open_line(invoice) | self._open_line(customer_invoice),
            [{"reconciled": True}, {"reconciled": True}],
        )
        self.assertTrue(payment.is_reconciled)

    def test_supplier_refund(self):
        invoice = self._create_invoice("in_invoice", 1000)
        refund = self._create_invoice("in_refund", 200)
        order = self._create_order(self._open_line(invoice) | self._open_line(refund))
        self._upload(order)
        payment = order.payment_ids
        self.assertEqual(payment.partner_bank_id, self.bank_a)
        self.assertRecordValues(
            payment.move_id.line_ids.sorted("balance"),
            [
                {"account_id": self.outstanding_account.id, "balance": -800},
                {"account_id": self.payable_account.id, "balance": -200},
                {"account_id": self.payable_account.id, "balance": 1000},
            ],
        )
        self.assertRecordValues(
            invoice | refund,
            [{"amount_residual": 0}, {"amount_residual": 0}],
        )
        self.assertTrue(payment.is_reconciled)

    def test_debit_entry_any_reconcilable_account(self):
        dividend_account = self.env["account.account"].create(
            {
                "name": "Dividends due",
                "code": "451100",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        invoice = self._create_invoice("in_invoice", 1000)
        dividend = self._create_debit_entry(dividend_account, 400)
        order = self._create_order(self._open_line(invoice) | self._open_line(dividend))
        self._upload(order)
        payment = order.payment_ids
        self.assertRecordValues(
            payment.move_id.line_ids.sorted("balance"),
            [
                {"account_id": self.outstanding_account.id, "balance": -600},
                {"account_id": dividend_account.id, "balance": -400},
                {"account_id": self.payable_account.id, "balance": 1000},
            ],
        )
        self.assertRecordValues(
            self._open_line(invoice) | self._open_line(dividend),
            [{"reconciled": True}, {"reconciled": True}],
        )
        self.assertTrue(payment.is_reconciled)

    def test_negative_group_refused(self):
        invoice = self._create_invoice("in_invoice", 100)
        customer_invoice = self._create_invoice("out_invoice", 300)
        order = self._create_order(
            self._open_line(invoice) | self._open_line(customer_invoice)
        )
        order.payment_line_ids.partner_bank_id = self.bank_a
        with self.assertRaisesRegex(UserError, "Netting Partner.*FR7600001"):
            self._confirm(order)

    def test_negative_bank_account_group_refused(self):
        invoice = self._create_invoice("in_invoice", 1000)
        customer_invoice = self._create_invoice("out_invoice", 300)
        order = self._create_order(self._open_line(invoice))
        order.payment_line_ids.partner_bank_id = self.bank_a
        self._open_line(customer_invoice).create_payment_line_from_move_line(
            order
        ).partner_bank_id = self.bank_b
        with self.assertRaisesRegex(UserError, "Netting Partner.*FR7600002"):
            self._confirm(order)

    def test_partial_line(self):
        invoice = self._create_invoice("in_invoice", 1000)
        customer_invoice = self._create_invoice("out_invoice", 300)
        order = self._create_order(
            self._open_line(invoice) | self._open_line(customer_invoice)
        )
        order.payment_line_ids.filtered(
            lambda line: line.amount_currency < 0
        ).amount_currency = -100
        self._upload(order)
        self.assertRecordValues(order.payment_ids, [{"amount": 900}])
        self.assertRecordValues(
            invoice | customer_invoice,
            [{"amount_residual": 0}, {"amount_residual": 200}],
        )
        self.assertTrue(order.payment_ids.is_reconciled)

    def test_group_ignores_account_and_date(self):
        other_payable = self.env["account.account"].create(
            {
                "name": "Other payable",
                "code": "401199",
                "account_type": "liability_payable",
                "reconcile": True,
            }
        )
        today = fields.Date.context_today(self.env.user)
        invoice = self._create_invoice(
            "in_invoice", 1000, date_due=today + timedelta(days=10)
        )
        other_invoice = self._create_invoice(
            "in_invoice",
            500,
            date_due=today + timedelta(days=20),
            open_account=other_payable,
        )
        order = self._create_order(
            self._open_line(invoice) | self._open_line(other_invoice)
        )
        order.date_prefered = "due"
        self._confirm(order)
        self.assertRecordValues(order.payment_ids, [{"amount": 1500, "date": today}])
        self.assertRecordValues(order.payment_lot_ids, [{"date": today}])

    def test_structured_reference_refused(self):
        invoice = self._create_invoice("in_invoice", 1000)
        customer_invoice = self._create_invoice("out_invoice", 300)
        order = self._create_order(
            self._open_line(invoice) | self._open_line(customer_invoice)
        )
        order.payment_line_ids.communication_type = "structured"
        with self.assertRaisesRegex(UserError, "structured reference"):
            self._confirm(order)

    def test_sorted_by_amount_desc(self):
        customer_invoice = self._create_invoice("out_invoice", 300)
        small_invoice = self._create_invoice("in_invoice", 200)
        invoice = self._create_invoice("in_invoice", 1000)
        order = self._create_order(
            self._open_line(customer_invoice)
            | self._open_line(small_invoice)
            | self._open_line(invoice)
        )
        self._confirm(order)
        communication = {
            line.move_line_id.move_id: line.communication
            for line in order.payment_line_ids
        }
        self.assertRecordValues(
            order.payment_ids,
            [
                {
                    "amount": 900,
                    "partner_type": "supplier",
                    "destination_account_id": self.payable_account.id,
                    "payment_reference": " - ".join(
                        [
                            communication[invoice],
                            communication[small_invoice],
                            communication[customer_invoice],
                        ]
                    ),
                }
            ],
        )

    def test_cancel_and_redo(self):
        invoice = self._create_invoice("in_invoice", 1000)
        customer_invoice = self._create_invoice("out_invoice", 300)
        order = self._create_order(
            self._open_line(invoice) | self._open_line(customer_invoice)
        )
        self._upload(order)
        move = order.payment_ids.move_id
        order.action_cancel()
        self.assertTrue(not move.exists() or move.state == "cancel")
        self.assertRecordValues(
            invoice | customer_invoice,
            [{"amount_residual": 1000}, {"amount_residual": 300}],
        )
        order.cancel2draft()
        self._upload(order)
        self.assertRecordValues(
            invoice | customer_invoice,
            [{"amount_residual": 0}, {"amount_residual": 0}],
        )

    def test_mode_without_netting(self):
        mode = self.netting_mode.copy({"name": "Plain transfer", "netting": False})
        invoice = self._create_invoice("in_invoice", 1000)
        customer_invoice = self._create_invoice("out_invoice", 300)
        order = self._create_order(
            self._open_line(invoice) | self._open_line(customer_invoice), mode=mode
        )
        with self.assertRaisesRegex(UserError, "negative or null"):
            self._confirm(order)

    def test_mode_without_netting_groups_by_account(self):
        mode = self.netting_mode.copy({"name": "Plain transfer", "netting": False})
        other_payable = self.env["account.account"].create(
            {
                "name": "Other payable",
                "code": "401199",
                "account_type": "liability_payable",
                "reconcile": True,
            }
        )
        invoice = self._create_invoice("in_invoice", 1000)
        other_invoice = self._create_invoice(
            "in_invoice", 500, open_account=other_payable
        )
        order = self._create_order(
            self._open_line(invoice) | self._open_line(other_invoice), mode=mode
        )
        self._confirm(order)
        self.assertEqual(sorted(order.payment_ids.mapped("amount")), [500, 1000])

    def test_negative_line_eligibility(self):
        invoice = self._create_invoice("in_invoice", 1000)
        customer_invoice = self._create_invoice("out_invoice", 300)
        order = self._create_order(
            self._open_line(invoice) | self._open_line(customer_invoice)
        )
        payable_line, receivable_line = order.payment_line_ids.sorted(
            "amount_currency", reverse=True
        )
        with self.assertRaisesRegex(ValidationError, "residual"):
            receivable_line.amount_currency = -400
        with self.assertRaisesRegex(ValidationError, "debit"):
            payable_line.amount_currency = -100
        with self.assertRaisesRegex(ValidationError, "debit"):
            self.env["account.payment.line"].create(
                {
                    "order_id": order.id,
                    "partner_id": self.partner.id,
                    "communication": "Manual",
                    "amount_currency": -50,
                }
            )

    def test_payment_edit_keeps_netting_lines(self):
        invoice = self._create_invoice("in_invoice", 1000)
        customer_invoice = self._create_invoice("out_invoice", 300)
        order = self._create_order(
            self._open_line(invoice) | self._open_line(customer_invoice)
        )
        self._upload(order)
        payment = order.payment_ids
        payment.move_id.button_draft()
        payment.payment_reference = "Edited"
        self.assertRecordValues(
            payment.move_id.line_ids.sorted("balance"),
            [
                {"account_id": self.outstanding_account.id, "balance": -700},
                {"account_id": self.receivable_account.id, "balance": -300},
                {"account_id": self.payable_account.id, "balance": 1000},
            ],
        )
