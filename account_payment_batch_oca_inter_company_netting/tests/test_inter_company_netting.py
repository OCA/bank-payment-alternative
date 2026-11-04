# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account_invoice_inter_company.tests.test_inter_company_invoice import (
    TestAccountInvoiceInterCompanyBase,
)
from odoo.addons.account_payment_batch_oca_netting.tests.common import NettingCommon


@tagged("post_install", "-at_install")
class TestInterCompanyNetting(NettingCommon, TestAccountInvoiceInterCompanyBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.company_ids |= cls.company_a | cls.company_b
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                allowed_company_ids=[cls.company_b.id, cls.company_a.id],
            )
        )
        cls.netting_mode = cls.env["account.payment.method.line"].create(
            {
                "name": "Inter company netting transfer",
                "company_id": cls.company_b.id,
                "journal_id": cls.bank_journal_company_b.id,
                "payment_method_id": cls.netting_mode.payment_method_id.id,
                "payment_account_id": cls._create_outstanding_account(cls.company_b).id,
                "selectable": True,
                "group_lines": True,
                "netting": True,
            }
        )
        cls.outstanding_account_company_a = cls._create_outstanding_account(
            cls.company_a
        )
        cls.bank_journal_company_a.inbound_payment_method_line_ids[
            :1
        ].payment_account_id = cls.outstanding_account_company_a
        cls.bank_journal_company_a.bank_account_id = cls._create_bank_account(
            "FR7630004000031234567890143", cls.partner_company_a
        )
        cls.bank_journal_company_b.bank_account_id = cls._create_bank_account(
            "FR7630001007941234567890185", cls.partner_company_b
        )
        cls.partner_company_a.with_company(cls.company_b).write(
            {
                "property_account_receivable_id": cls.a_recv_company_b.id,
                "property_account_payable_id": cls.a_pay_company_b.id,
            }
        )
        cls.product_consultant_multi_company.with_company(cls.company_a).write(
            {
                "property_account_income_id": cls.a_sale_company_a.id,
                "property_account_expense_id": cls.a_expense_company_a.id,
            }
        )
        cls.product_consultant_multi_company.with_company(cls.company_b).write(
            {
                "property_account_income_id": cls.a_sale_company_b.id,
                "property_account_expense_id": cls.a_expense_company_b.id,
            }
        )
        cls.dividend_receivable_account = cls._create_dividend_account(
            "X4511", "asset_current", cls.company_b
        )
        cls.dividend_payable_account = cls._create_dividend_account(
            "X4570", "liability_current", cls.company_a
        )
        cls.company_b.interco_dividend_receivable_account_id = (
            cls.dividend_receivable_account
        )
        cls.company_a.interco_dividend_payable_account_id = cls.dividend_payable_account
        cls.company_a.interco_netting_journal_id = cls.misc_journal_company_a

    @classmethod
    def _create_dividend_account(cls, code, account_type, company):
        return cls.env["account.account"].create(
            {
                "code": code,
                "name": f"Dividends {code}",
                "account_type": account_type,
                "reconcile": True,
                "company_ids": [Command.link(company.id)],
            }
        )

    @classmethod
    def _create_outstanding_account(cls, company):
        return cls.env["account.account"].create(
            {
                "code": f"X5118.{company.name[-1]}",
                "name": f"Outstanding - ({company.name})",
                "account_type": "asset_current",
                "reconcile": True,
                "company_ids": [Command.link(company.id)],
            }
        )

    @classmethod
    def _create_bank_account(cls, acc_number, partner):
        return cls.env["res.partner.bank"].create(
            {
                "acc_number": acc_number,
                "partner_id": partner.id,
                "allow_out_payment": True,
            }
        )

    def _post_invoice(self, company, partner, journal, move_type, amount):
        invoice = (
            self.env["account.move"]
            .with_company(company)
            .create(
                {
                    "move_type": move_type,
                    "partner_id": partner.id,
                    "journal_id": journal.id,
                    "invoice_date": "2026-01-15",
                    "ref": f"{move_type} {amount}",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": self.product_consultant_multi_company.id,
                                "quantity": 1,
                                "name": f"{move_type} {amount}",
                                "price_unit": amount,
                                "tax_ids": [Command.clear()],
                            }
                        )
                    ],
                }
            )
        )
        invoice.action_post()
        return invoice

    def _post_customer_invoice_company_a(self, amount):
        return self._post_invoice(
            self.company_a,
            self.partner_company_b,
            self.sales_journal_company_a,
            "out_invoice",
            amount,
        )

    def _post_customer_invoice_company_b(self, amount):
        return self._post_invoice(
            self.company_b,
            self.partner_company_a,
            self.sales_journal_company_b,
            "out_invoice",
            amount,
        )

    def _post_customer_refund_company_a(self, amount):
        return self._post_invoice(
            self.company_a,
            self.partner_company_b,
            self.sales_journal_company_a,
            "out_refund",
            amount,
        )

    def _get_linked_invoice(self, invoice):
        return self.env["account.move"].search(
            [
                ("auto_invoice_id", "=", invoice.id),
                ("company_id", "!=", invoice.company_id.id),
            ],
            limit=1,
        )

    def _post_entry(self, journal, account, counterpart, balance, partner):
        entry = (
            self.env["account.move"]
            .with_company(journal.company_id)
            .create(
                {
                    "move_type": "entry",
                    "journal_id": journal.id,
                    "date": "2026-01-15",
                    "line_ids": [
                        Command.create(
                            {
                                "name": "Dividend",
                                "account_id": account.id,
                                "partner_id": partner.id,
                                "balance": balance,
                            }
                        ),
                        Command.create(
                            {
                                "name": "Counterpart",
                                "account_id": counterpart.id,
                                "balance": -balance,
                            }
                        ),
                    ],
                }
            )
        )
        entry.action_post()
        return entry

    def _post_dividend_receivable(self):
        return self._post_entry(
            self.misc_journal_company_b,
            self.dividend_receivable_account,
            self.a_sale_company_b,
            300.0,
            self.partner_company_a,
        )

    def _post_dividend_payable(self, amount, partner):
        return self._post_entry(
            self.misc_journal_company_a,
            self.dividend_payable_account,
            self.a_expense_company_a,
            -amount,
            partner,
        )

    def _dividend_line(self, entry):
        return entry.line_ids.filtered(
            lambda line: line.account_id
            in self.dividend_receivable_account | self.dividend_payable_account
        )

    def _post_supplier_invoice_company_b(self):
        return self._get_linked_invoice(self._post_customer_invoice_company_a(1000.0))

    def _upload_netted_dividend(self):
        return self._upload_netted(
            self._post_supplier_invoice_company_b() | self._post_dividend_receivable()
        )

    def _upload_netted(self, invoices):
        return self._upload(self._create_order(self._open_line(invoices)))

    def _mirror_move_line(self, mirror, account):
        return mirror.line_ids.filtered(lambda line: line.account_id == account)

    def _mirror_line(self, order, account):
        return self._mirror_move_line(order.payment_ids.auto_move_id, account)

    def _assert_mirror_reconciled(self, mirror_line, invoice):
        invoice_line = invoice.line_ids.filtered(
            lambda line: line.account_id == mirror_line.account_id
        )
        self.assertTrue(mirror_line.reconciled)
        self.assertEqual(mirror_line.full_reconcile_id, invoice_line.full_reconcile_id)

    def _assert_dividend_left_open(self, order, candidates):
        mirror_line = self._mirror_line(order, self.dividend_payable_account)
        self.assertEqual(mirror_line.balance, 300.0)
        self.assertFalse(mirror_line.reconciled)
        self.assertFalse(self._dividend_line(candidates).filtered("reconciled"))
        auto_move = order.payment_ids.auto_move_id
        self.assertTrue(
            order.message_ids.filtered(
                lambda message: auto_move.name in (message.body or "")
                and "no single posted linked entry" in message.body
            )
        )
        self.assertTrue(self._mirror_line(order, self.a_recv_company_a).reconciled)

    def test_netted_customer_invoice_with_link(self):
        customer_invoice_a = self._post_customer_invoice_company_a(1000.0)
        supplier_invoice_b = self._get_linked_invoice(customer_invoice_a)
        customer_invoice_b = self._post_customer_invoice_company_b(300.0)
        supplier_invoice_a = self._get_linked_invoice(customer_invoice_b)

        order = self._upload_netted(supplier_invoice_b | customer_invoice_b)

        payment = order.payment_ids
        self.assertEqual(payment.amount, 700.0)
        auto_move = payment.auto_move_id
        self.assertEqual(auto_move.company_id, self.company_a)
        self.assertEqual(auto_move.journal_id, self.bank_journal_company_a)
        self.assertEqual(auto_move.date, payment.date)
        self.assertEqual(auto_move.state, "posted")
        self.assertEqual(len(auto_move.line_ids), 3)
        self.assertEqual(
            self._mirror_line(order, self.outstanding_account_company_a).balance, 700.0
        )
        receivable_line = self._mirror_line(order, self.a_recv_company_a)
        self.assertEqual(receivable_line.balance, -1000.0)
        self._assert_mirror_reconciled(receivable_line, customer_invoice_a)
        payable_line = self._mirror_line(order, self.a_pay_company_a)
        self.assertEqual(payable_line.balance, 300.0)
        self._assert_mirror_reconciled(payable_line, supplier_invoice_a)
        for invoice in (
            supplier_invoice_b,
            customer_invoice_b,
            customer_invoice_a,
            supplier_invoice_a,
        ):
            self.assertTrue(invoice.currency_id.is_zero(invoice.amount_residual))

    def test_netted_customer_invoice_without_link(self):
        supplier_invoice_b = self._get_linked_invoice(
            self._post_customer_invoice_company_a(1000.0)
        )
        self.company_b.intercompany_invoicing = False
        unlinked_invoice = self._post_customer_invoice_company_b(300.0)
        self.assertFalse(self._get_linked_invoice(unlinked_invoice))

        order = self._upload_netted(supplier_invoice_b | unlinked_invoice)

        payable_line = self._mirror_line(order, self.a_pay_company_a)
        self.assertEqual(payable_line.balance, 300.0)
        self.assertFalse(payable_line.reconciled)
        unlinked_payment_line = order.payment_line_ids.filtered(
            lambda line: line.amount_currency < 0
        )
        auto_move = order.payment_ids.auto_move_id
        self.assertTrue(
            order.message_ids.filtered(
                lambda message: auto_move.name in (message.body or "")
                and unlinked_payment_line.communication in message.body
            )
        )
        self.assertTrue(
            self._mirror_line(order, self.a_recv_company_a).reconciled,
            "the linked line of the same mirror stays reconciled",
        )

    def test_multi_counterpart_mirror_balanced(self):
        supplier_invoice_b = self._get_linked_invoice(
            self._post_customer_invoice_company_a(1000.0)
        )
        customer_invoice_b = self._post_customer_invoice_company_b(300.0)
        supplier_refund_b = self._get_linked_invoice(
            self._post_customer_refund_company_a(200.0)
        )

        order = self._upload_netted(
            supplier_invoice_b | customer_invoice_b | supplier_refund_b
        )

        payment = order.payment_ids
        self.assertEqual(payment.amount, 500.0)
        self.assertEqual(len(payment.payment_line_ids), 3)
        line_balances = sorted(payment.auto_move_id.line_ids.mapped("balance"))
        self.assertEqual(line_balances, [-1000.0, 200.0, 300.0, 500.0])
        self.assertEqual(
            self._mirror_line(order, self.outstanding_account_company_a).balance, 500.0
        )
        unreconciled = payment.auto_move_id.line_ids.filtered(
            lambda line: line.account_id.reconcile
            and line.account_id != self.outstanding_account_company_a
            and not line.reconciled
        )
        self.assertFalse(unreconciled)

    def test_dividend_unique_candidate_reconciled(self):
        candidate = self._post_dividend_payable(300.0, self.partner_company_b)

        order = self._upload_netted_dividend()

        self.assertEqual(order.payment_ids.amount, 700.0)
        mirror_line = self._mirror_line(order, self.dividend_payable_account)
        self.assertEqual(mirror_line.balance, 300.0)
        self.assertEqual(mirror_line.partner_id, self.partner_company_b)
        self._assert_mirror_reconciled(mirror_line, candidate)

    def test_dividend_candidate_without_partner_reconciled(self):
        candidate = self._post_dividend_payable(300.0, self.env["res.partner"])

        order = self._upload_netted_dividend()

        mirror_line = self._mirror_line(order, self.dividend_payable_account)
        self.assertEqual(mirror_line.partner_id, self.partner_company_b)
        self._assert_mirror_reconciled(mirror_line, candidate)

    def test_dividend_two_candidates_left_open(self):
        candidates = self._post_dividend_payable(
            300.0, self.partner_company_b
        ) | self._post_dividend_payable(300.0, self.env["res.partner"])

        order = self._upload_netted_dividend()

        self._assert_dividend_left_open(order, candidates)

    def test_dividend_residual_mismatch_left_open(self):
        candidate = self._post_dividend_payable(500.0, self.partner_company_b)

        order = self._upload_netted_dividend()

        self._assert_dividend_left_open(order, candidate)

    def test_dividend_candidate_of_other_partner_ignored(self):
        candidate = self._post_dividend_payable(300.0, self.partner_company_a)

        order = self._upload_netted_dividend()

        self._assert_dividend_left_open(order, candidate)

    def test_dividend_other_residual_does_not_make_ambiguous(self):
        self._post_dividend_payable(500.0, self.partner_company_b)
        candidate = self._post_dividend_payable(300.0, self.partner_company_b)

        order = self._upload_netted_dividend()

        mirror_line = self._mirror_line(order, self.dividend_payable_account)
        self._assert_mirror_reconciled(mirror_line, candidate)

    def test_two_dividends_of_same_amount_left_open(self):
        candidate = self._post_dividend_payable(300.0, self.partner_company_b)
        dividends = self._post_dividend_receivable() | self._post_dividend_receivable()

        order = self._upload_netted(self._post_supplier_invoice_company_b() | dividends)

        mirror_lines = self._mirror_line(order, self.dividend_payable_account)
        self.assertEqual(mirror_lines.mapped("balance"), [300.0, 300.0])
        self.assertFalse(mirror_lines.filtered("reconciled"))
        self.assertFalse(self._dividend_line(candidate).reconciled)

    def test_dividend_payable_account_not_set(self):
        self.company_a.interco_dividend_payable_account_id = False
        order = self._create_order(
            self._open_line(
                self._post_supplier_invoice_company_b()
                | self._post_dividend_receivable()
            )
        )
        order.draft2open()
        order.open2generated()

        with self.assertRaisesRegex(UserError, "dividend payable account"):
            order.generated2uploaded()

    def test_receivable_setting_not_set_is_not_a_dividend(self):
        self.company_b.interco_dividend_receivable_account_id = False

        order = self._upload_netted_dividend()

        self.assertFalse(self._mirror_line(order, self.dividend_payable_account))
        self.assertEqual(self._mirror_line(order, self.a_pay_company_a).balance, 300.0)

    def _create_net_zero_order(self):
        customer_invoice_a = self._post_customer_invoice_company_a(300.0)
        customer_invoice_b = self._post_customer_invoice_company_b(300.0)
        order = self._create_order(
            self._open_line(
                self._get_linked_invoice(customer_invoice_a) | customer_invoice_b
            )
        )
        return order, customer_invoice_a, self._get_linked_invoice(customer_invoice_b)

    def _net_zero_mirror_line(self, order, account):
        return self._mirror_move_line(
            order.netting_move_ids.netting_auto_move_id, account
        )

    def test_net_zero_mirror_in_netting_journal(self):
        order, customer_invoice_a, supplier_invoice_a = self._create_net_zero_order()

        self._upload(order)

        self.assertFalse(order.payment_ids)
        source = order.netting_move_ids
        mirror = source.netting_auto_move_id
        self.assertRecordValues(
            mirror,
            [
                {
                    "company_id": self.company_a.id,
                    "journal_id": self.misc_journal_company_a.id,
                    "date": source.date,
                    "ref": order.name,
                    "state": "posted",
                }
            ],
        )
        self.assertEqual(len(mirror.line_ids), 2)
        receivable_line = self._net_zero_mirror_line(order, self.a_recv_company_a)
        self.assertEqual(receivable_line.balance, -300.0)
        self._assert_mirror_reconciled(receivable_line, customer_invoice_a)
        payable_line = self._net_zero_mirror_line(order, self.a_pay_company_a)
        self.assertEqual(payable_line.balance, 300.0)
        self._assert_mirror_reconciled(payable_line, supplier_invoice_a)

    def test_net_zero_mirror_journal_not_set(self):
        self.company_a.interco_netting_journal_id = False
        order, _customer_invoice_a, _supplier_invoice_a = self._create_net_zero_order()
        order.draft2open()
        order.open2generated()

        with self.assertRaisesRegex(UserError, "netting journal is not set"):
            order.generated2uploaded()

    def test_net_zero_mirror_of_dividend(self):
        candidate = self._post_dividend_payable(300.0, self.partner_company_b)
        supplier_invoice_b = self._get_linked_invoice(
            self._post_customer_invoice_company_a(300.0)
        )

        order = self._upload_netted(
            supplier_invoice_b | self._post_dividend_receivable()
        )

        mirror_line = self._net_zero_mirror_line(order, self.dividend_payable_account)
        self.assertEqual(mirror_line.balance, 300.0)
        self.assertEqual(mirror_line.partner_id, self.partner_company_b)
        self._assert_mirror_reconciled(mirror_line, candidate)

    def test_net_zero_without_receiving_company_has_no_mirror(self):
        self.company_a.interco_netting_journal_id = False

        partner = self.env["res.partner"].create({"name": "External Partner"})
        partner.with_company(self.company_b).write(
            {
                "property_account_receivable_id": self.a_recv_company_b.id,
                "property_account_payable_id": self.a_pay_company_b.id,
            }
        )
        supplier_invoice = self._post_invoice(
            self.company_b,
            partner,
            self.purchases_journal_company_b,
            "in_invoice",
            500.0,
        )
        customer_invoice = self._post_invoice(
            self.company_b,
            partner,
            self.sales_journal_company_b,
            "out_invoice",
            500.0,
        )

        order = self._upload_netted(supplier_invoice | customer_invoice)

        self.assertEqual(order.netting_move_ids.state, "posted")
        self.assertFalse(order.netting_move_ids.netting_auto_move_id)

    def test_net_zero_mirror_cancel_and_redo(self):
        order, customer_invoice_a, supplier_invoice_a = self._create_net_zero_order()
        self._upload(order)
        mirror = order.netting_move_ids.netting_auto_move_id

        order.action_cancel()

        self.assertEqual(mirror.state, "cancel")
        self.assertEqual(customer_invoice_a.amount_residual, 300.0)
        self.assertEqual(supplier_invoice_a.amount_residual, 300.0)

        order.cancel2draft()

        self.assertFalse(mirror.exists())

        self._upload(order)

        self.assertEqual(order.netting_move_ids.netting_auto_move_id.state, "posted")
        self.assertEqual(customer_invoice_a.amount_residual, 0.0)
        self.assertEqual(supplier_invoice_a.amount_residual, 0.0)

    def test_net_zero_source_reset_to_draft_resets_mirror(self):
        order, customer_invoice_a, _supplier_invoice_a = self._create_net_zero_order()
        self._upload(order)
        source = order.netting_move_ids
        mirror = source.netting_auto_move_id

        source.button_draft()

        self.assertEqual(mirror.state, "draft")
        self.assertEqual(customer_invoice_a.amount_residual, 300.0)

    def test_net_zero_source_in_draft_then_order_cancel_deletes_mirror(self):
        order, customer_invoice_a, _supplier_invoice_a = self._create_net_zero_order()
        self._upload(order)
        source = order.netting_move_ids
        mirror = source.netting_auto_move_id
        source.button_draft()

        order.action_cancel()

        self.assertFalse(source.exists())
        self.assertFalse(mirror.exists())
        self.assertEqual(customer_invoice_a.amount_residual, 300.0)

    def test_payment_line_without_journal_item_not_matched_to_any_entry(self):
        supplier_invoice_b = self._post_supplier_invoice_company_b()
        self.company_a.intercompany_invoicing = False
        unrelated_invoice = self._post_customer_invoice_company_a(500.0)
        self.assertFalse(self._get_linked_invoice(unrelated_invoice))
        order = self._create_order(self._open_line(supplier_invoice_b))
        self.env["account.payment.line"].create(
            {
                "order_id": order.id,
                "partner_id": self.partner_company_a.id,
                "partner_bank_id": order.payment_line_ids.partner_bank_id.id,
                "currency_id": order.payment_line_ids.currency_id.id,
                "amount_currency": 200.0,
                "communication": "Manual line",
                "communication_type": "free",
            }
        )

        self._upload(order)

        self.assertEqual(order.payment_ids.amount, 1200.0)
        mirror_lines = self._mirror_line(order, self.a_recv_company_a).filtered(
            lambda line: line.name == "Manual line"
        )
        self.assertEqual(mirror_lines.balance, -200.0)
        self.assertFalse(mirror_lines.reconciled)
        self.assertEqual(unrelated_invoice.amount_residual, 500.0)
