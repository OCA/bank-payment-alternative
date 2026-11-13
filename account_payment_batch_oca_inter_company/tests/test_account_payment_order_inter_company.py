# Copyright 2022 Akretion France (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import UserError

from odoo.addons.account_invoice_inter_company.tests.test_inter_company_invoice import (
    TestAccountInvoiceInterCompanyBase,
)


class TestAccountPaymentOrderInterCompany(TestAccountInvoiceInterCompanyBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.env.user.groups_id = [
            Command.link(
                cls.env.ref("account_payment_batch_oca.group_account_payment").id
            )
        ]
        payment_method_out, payment_method_in = (
            cls.env["account.payment.method"]
            .sudo()
            .create(
                [
                    {
                        "name": f"Inter company test {payment_type}",
                        "code": "test_manual",
                        "payment_type": payment_type,
                        "payment_order_ok": True,
                        "bank_account_required": True,
                    }
                    for payment_type in ("outbound", "inbound")
                ]
            )
        )
        cls.outstanding_account_company_a = cls._create_outstanding_account(
            cls.company_a
        )
        cls.outstanding_account_company_b = cls._create_outstanding_account(
            cls.company_b
        )
        cls.payment_mode_company_b = cls.env["account.payment.method.line"].create(
            {
                "name": "Test Credit Transfer to Suppliers",
                "company_id": cls.company_b.id,
                "journal_id": cls.bank_journal_company_b.id,
                "payment_method_id": payment_method_out.id,
                "payment_account_id": cls.outstanding_account_company_b.id,
                "selectable": True,
            }
        )
        cls.payment_mode_company_a = cls.env["account.payment.method.line"].create(
            {
                "name": "Test Direct Debit of customers",
                "company_id": cls.company_a.id,
                "journal_id": cls.bank_journal_company_a.id,
                "payment_method_id": payment_method_in.id,
                "payment_account_id": cls.outstanding_account_company_a.id,
                "selectable": True,
            }
        )
        cls.partner_bank_company_b = cls.env["res.partner.bank"].create(
            {
                "acc_number": "FR7630001007941234567890185",
                "partner_id": cls.company_b.partner_id.id,
                "allow_out_payment": True,
            }
        )
        cls.bank_journal_company_b.bank_account_id = cls.partner_bank_company_b
        cls.partner_bank_company_a = cls.env["res.partner.bank"].create(
            {
                "acc_number": "FR7630004000031234567890143",
                "partner_id": cls.company_a.partner_id.id,
                "allow_out_payment": True,
            }
        )
        cls.bank_journal_company_a.bank_account_id = cls.partner_bank_company_a
        cls.partner_company_a.with_company(cls.company_b).write(
            {
                "property_account_receivable_id": cls.a_recv_company_b.id,
                "property_account_payable_id": cls.a_pay_company_b.id,
            }
        )
        cls.invoice_company_b = cls.account_move_obj.with_company(cls.company_b).create(
            {
                "move_type": "in_invoice",
                "partner_id": cls.partner_company_a.id,
                "invoice_date": "2026-01-15",
                "journal_id": cls.purchases_journal_company_b.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": cls.product_consultant_multi_company.id,
                            "quantity": 1,
                            "product_uom_id": cls.env.ref("uom.product_uom_hour").id,
                            "account_id": cls.a_expense_company_b.id,
                            "name": "Service Multi Company",
                            "price_unit": 450.0,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
        cls.product_consultant_multi_company.with_company(
            cls.company_a
        ).property_account_income_id = cls.a_sale_company_a

    @classmethod
    def _create_outstanding_account(cls, company):
        return cls.env["account.account"].create(
            {
                "code": f"X5112.{company.name[-1]}",
                "name": f"Outstanding - ({company.name})",
                "account_type": "asset_current",
                "reconcile": True,
                "company_ids": [Command.link(company.id)],
            }
        )

    def _create_intercompany_supplier_invoice(self):
        self.invoice_company_a.with_user(self.user_company_a).action_post()
        return self.account_move_obj.with_user(self.user_company_b).search(
            [
                ("auto_invoice_id", "=", self.invoice_company_a.id),
                ("company_id", "=", self.company_b.id),
            ],
            limit=1,
        )

    def _create_intercompany_customer_invoice(self):
        self.invoice_company_b.with_user(self.user_company_b).action_post()
        return self.account_move_obj.with_user(self.user_company_a).search(
            [
                ("auto_invoice_id", "=", self.invoice_company_b.id),
                ("company_id", "=", self.company_a.id),
            ],
            limit=1,
        )

    def _assert_reconciled(self, invoice):
        self.assertTrue(invoice.currency_id.is_zero(invoice.amount_residual))

    def _create_payment_order(self, invoice, payment_mode):
        invoice = invoice.with_env(self.env).with_company(invoice.company_id)
        invoice.preferred_payment_method_line_id = payment_mode
        invoice.create_account_payment_line()
        payment_order = invoice.line_ids.payment_line_ids.order_id
        payment_order.payment_line_ids.communication = invoice.name
        return payment_order

    def _pay_invoice(self, invoice, payment_mode, user=None):
        payment_order = self._create_payment_order(invoice, payment_mode).with_user(
            user or self.env.user
        )
        self._upload_payment_order(payment_order)
        return payment_order

    def _create_two_installment_term(self):
        return self.env["account.payment.term"].create(
            {
                "name": "30% now, 70% in 30 days",
                "line_ids": [
                    Command.create(
                        {"value": "percent", "value_amount": 30.0, "nb_days": 0}
                    ),
                    Command.create(
                        {"value": "percent", "value_amount": 70.0, "nb_days": 30}
                    ),
                ],
            }
        )

    def _create_supplier_invoice_with_installments(
        self, on_customer_invoice=True, on_supplier_invoice=True
    ):
        term = self._create_two_installment_term()
        if on_customer_invoice:
            self.invoice_company_a.invoice_payment_term_id = term
        if on_supplier_invoice:
            self.partner_company_a.with_company(
                self.company_b
            ).property_supplier_payment_term_id = term
        return self._create_intercompany_supplier_invoice()

    def _set_other_receivable_property_company_a(self):
        self.partner_company_b.with_company(
            self.company_a
        ).property_account_receivable_id = self.account_obj.create(
            {
                "code": "X4112.A",
                "name": "Other receivable - (Company A)",
                "account_type": "asset_receivable",
                "reconcile": True,
                "company_ids": [Command.link(self.company_a.id)],
            }
        )

    def _get_installments(self, invoice):
        return (
            invoice.sudo()
            .line_ids.filtered(lambda line: line.display_type == "payment_term")
            .sorted("date_maturity")
        )

    def _upload_payment_order(self, payment_order):
        payment_order.draft2open()
        payment_order.open2generated()
        payment_order.generated2uploaded()

    def _upload_unlinked_misc_entry(
        self, payment_mode, journal, partner_account, other_account, partner, balance
    ):
        company = payment_mode.company_id
        misc_move = self.account_move_obj.with_company(company).create(
            {
                "move_type": "entry",
                "journal_id": journal.id,
                "date": "2026-01-15",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": partner_account.id,
                            "partner_id": partner.id,
                            "balance": balance,
                        }
                    ),
                    Command.create(
                        {"account_id": other_account.id, "balance": -balance}
                    ),
                ],
            }
        )
        misc_move.action_post()
        payment_order = (
            self.env["account.payment.order"]
            .with_company(company)
            .create(
                {
                    "payment_method_line_id": payment_mode.id,
                    "payment_type": payment_mode.payment_type,
                    "company_id": company.id,
                }
            )
        )
        misc_move.line_ids.filtered(
            lambda line: line.account_id == partner_account
        ).create_payment_line_from_move_line(payment_order)
        payment_order.payment_line_ids.communication = "Misc entry"
        self._upload_payment_order(payment_order)
        return payment_order

    def _assert_unreconciled_message_posted(self, payment_order):
        auto_move = payment_order.payment_ids.auto_move_id
        communication = payment_order.payment_line_ids[0].communication
        self.assertTrue(
            payment_order.message_ids.filtered(
                lambda message: auto_move.name in (message.body or "")
                and communication in message.body
            )
        )

    def test_create_customer_invoice_and_pay_supplier_invoice(self):
        invoice_company_b = self._create_intercompany_supplier_invoice()
        payment_order = self._pay_invoice(
            invoice_company_b, self.payment_mode_company_b
        )
        self._assert_reconciled(invoice_company_b)
        self._assert_reconciled(self.invoice_company_a)
        auto_move = payment_order.payment_ids.auto_move_id
        self.assertEqual(auto_move.company_id, self.company_a)
        self.assertEqual(auto_move.journal_id, self.bank_journal_company_a)
        self.assertEqual(auto_move.ref, payment_order.payment_ids.memo)
        outstanding_line = auto_move.line_ids.filtered(
            lambda line: line.account_id == self.outstanding_account_company_a
        )
        self.assertEqual(outstanding_line.debit, 450.0)

    def test_mirror_account_from_linked_line(self):
        invoice_company_b = self._create_intercompany_supplier_invoice()
        linked_line = self.invoice_company_a.line_ids.filtered(
            lambda line: line.account_id == self.a_recv_company_a
        )
        self._set_other_receivable_property_company_a()
        payment_order = self._pay_invoice(
            invoice_company_b, self.payment_mode_company_b
        )
        mirror_line = payment_order.payment_ids.auto_move_id.line_ids.filtered(
            lambda line: line.reconciled
        )
        self.assertEqual(mirror_line.account_id, self.a_recv_company_a)
        self.assertEqual(mirror_line.full_reconcile_id, linked_line.full_reconcile_id)

    def test_mirror_unlinked_outbound_line_on_receivable_property(self):
        payment_order = self._upload_unlinked_misc_entry(
            self.payment_mode_company_b,
            self.misc_journal_company_b,
            self.a_pay_company_b,
            self.a_expense_company_b,
            self.partner_company_a,
            -300.0,
        )
        mirror_line = payment_order.payment_ids.auto_move_id.line_ids.filtered(
            lambda line: line.credit
        )
        self.assertEqual(
            mirror_line.account_id,
            self.partner_company_b.with_company(
                self.company_a
            ).property_account_receivable_id,
        )
        self.assertFalse(mirror_line.reconciled)
        self._assert_unreconciled_message_posted(payment_order)

    def test_mirror_unlinked_inbound_line_on_payable_property(self):
        payment_order = self._upload_unlinked_misc_entry(
            self.payment_mode_company_a,
            self.misc_journal_company_a,
            self.a_recv_company_a,
            self.a_sale_company_a,
            self.partner_company_b,
            300.0,
        )
        mirror_line = payment_order.payment_ids.auto_move_id.line_ids.filtered(
            lambda line: line.debit
        )
        self.assertEqual(
            mirror_line.account_id,
            self.partner_company_a.with_company(
                self.company_b
            ).property_account_payable_id,
        )
        self.assertFalse(mirror_line.reconciled)
        self._assert_unreconciled_message_posted(payment_order)

    def test_create_customer_invoice_and_pay_customer_invoice(self):
        invoice_company_b = self._create_intercompany_supplier_invoice()
        payment_order = self._pay_invoice(
            self.invoice_company_a, self.payment_mode_company_a
        )
        self._assert_reconciled(self.invoice_company_a)
        self._assert_reconciled(invoice_company_b)
        outstanding_line = payment_order.payment_ids.auto_move_id.line_ids.filtered(
            lambda line: line.account_id == self.outstanding_account_company_b
        )
        self.assertEqual(outstanding_line.credit, 450.0)

    def test_create_supplier_invoice_and_pay_supplier_invoice(self):
        invoice_company_a = self._create_intercompany_customer_invoice()
        self._pay_invoice(self.invoice_company_b, self.payment_mode_company_b)
        self._assert_reconciled(self.invoice_company_b)
        self._assert_reconciled(invoice_company_a)

    def test_create_supplier_invoice_and_pay_customer_invoice(self):
        invoice_company_a = self._create_intercompany_customer_invoice()
        self._pay_invoice(invoice_company_a, self.payment_mode_company_a)
        self._assert_reconciled(invoice_company_a)
        self._assert_reconciled(self.invoice_company_b)

    def test_pay_customer_invoice_with_draft_supplier_invoice(self):
        self.company_b.invoice_auto_validation = False
        self._create_intercompany_supplier_invoice()
        payment_order = self._pay_invoice(
            self.invoice_company_a, self.payment_mode_company_a
        )
        self._assert_reconciled(self.invoice_company_a)
        auto_move = payment_order.payment_ids.auto_move_id
        self.assertEqual(auto_move.state, "posted")
        self.assertFalse(auto_move.line_ids.full_reconcile_id)
        self._assert_unreconciled_message_posted(payment_order)

    def test_pay_customer_invoice_with_cancelled_supplier_invoice(self):
        self.company_b.invoice_auto_validation = False
        invoice_company_b = self._create_intercompany_supplier_invoice()
        invoice_company_b.sudo().button_cancel()
        payment_order = self._pay_invoice(
            self.invoice_company_a, self.payment_mode_company_a
        )
        self._assert_reconciled(self.invoice_company_a)
        auto_move = payment_order.payment_ids.auto_move_id
        self.assertEqual(auto_move.state, "posted")
        self.assertFalse(auto_move.line_ids.full_reconcile_id)
        self._assert_unreconciled_message_posted(payment_order)

    def test_pay_both_installments_in_one_order(self):
        self.payment_mode_company_b.default_date_prefered = "now"
        invoice_company_b = self._create_supplier_invoice_with_installments()
        dest_installments = self._get_installments(self.invoice_company_a)
        self.assertEqual(dest_installments.mapped("debit"), [135.0, 315.0])
        payment_order = self._pay_invoice(
            invoice_company_b, self.payment_mode_company_b
        )
        self.assertEqual(len(payment_order.payment_ids), 1)
        self._assert_reconciled(invoice_company_b)
        self._assert_reconciled(self.invoice_company_a)
        mirror_lines = payment_order.payment_ids.auto_move_id.line_ids
        for dest_installment in dest_installments:
            mirror_line = (
                mirror_lines & dest_installment.full_reconcile_id.reconciled_line_ids
            )
            self.assertEqual(mirror_line.credit, dest_installment.debit)

    def test_pay_second_installment_only(self):
        invoice_company_b = self._create_supplier_invoice_with_installments()
        first_installment, second_installment = self._get_installments(
            self.invoice_company_a
        )
        payment_order = self._create_payment_order(
            invoice_company_b, self.payment_mode_company_b
        )
        first_paid_installment = self._get_installments(invoice_company_b)[0]
        payment_order.payment_line_ids.filtered(
            lambda line: line.move_line_id == first_paid_installment
        ).unlink()
        self._upload_payment_order(payment_order)
        self.assertTrue(second_installment.reconciled)
        self.assertFalse(first_installment.matched_credit_ids)

    def test_dest_with_more_installments_left_unreconciled_on_linked_account(self):
        invoice_company_b = self._create_supplier_invoice_with_installments(
            on_supplier_invoice=False
        )
        self.assertEqual(len(self._get_installments(invoice_company_b)), 1)
        self.assertEqual(len(self._get_installments(self.invoice_company_a)), 2)
        self._set_other_receivable_property_company_a()
        payment_order = self._pay_invoice(
            invoice_company_b, self.payment_mode_company_b
        )
        self._assert_reconciled(invoice_company_b)
        self.assertFalse(self.invoice_company_a.line_ids.matched_credit_ids)
        auto_move = payment_order.payment_ids.auto_move_id
        self.assertFalse(auto_move.line_ids.full_reconcile_id)
        mirror_line = auto_move.line_ids.filtered("credit")
        self.assertEqual(mirror_line.account_id, self.a_recv_company_a)
        self.assertEqual(mirror_line.partner_id, self.partner_company_b)
        self._assert_unreconciled_message_posted(payment_order)

    def test_payer_with_more_installments_left_unreconciled_on_linked_account(self):
        self.payment_mode_company_b.default_date_prefered = "now"
        invoice_company_b = self._create_supplier_invoice_with_installments(
            on_customer_invoice=False
        )
        self.assertEqual(len(self._get_installments(invoice_company_b)), 2)
        self.assertEqual(len(self._get_installments(self.invoice_company_a)), 1)
        self._set_other_receivable_property_company_a()
        payment_order = self._pay_invoice(
            invoice_company_b, self.payment_mode_company_b
        )
        self._assert_reconciled(invoice_company_b)
        self.assertFalse(self.invoice_company_a.line_ids.matched_credit_ids)
        auto_move = payment_order.payment_ids.auto_move_id
        self.assertFalse(auto_move.line_ids.full_reconcile_id)
        mirror_lines = auto_move.line_ids.filtered("credit")
        self.assertEqual(mirror_lines.mapped("credit"), [135.0, 315.0])
        self.assertEqual(mirror_lines.account_id, self.a_recv_company_a)
        self._assert_unreconciled_message_posted(payment_order)

    def test_installment_already_paid_left_unreconciled(self):
        self.payment_mode_company_b.default_date_prefered = "now"
        invoice_company_b = self._create_supplier_invoice_with_installments()
        first_installment, second_installment = self._get_installments(
            self.invoice_company_a
        )
        other_payment = self.account_move_obj.with_company(self.company_a).create(
            {
                "move_type": "entry",
                "date": "2026-01-15",
                "journal_id": self.bank_journal_company_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": first_installment.account_id.id,
                            "partner_id": first_installment.partner_id.id,
                            "credit": 135.0,
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.outstanding_account_company_a.id,
                            "debit": 135.0,
                        }
                    ),
                ],
            }
        )
        other_payment.action_post()
        (
            first_installment
            | other_payment.line_ids.filtered(
                lambda line: line.account_id == first_installment.account_id
            )
        ).reconcile()
        payment_order = self._pay_invoice(
            invoice_company_b, self.payment_mode_company_b
        )
        self._assert_reconciled(invoice_company_b)
        self.assertTrue(second_installment.reconciled)
        self.assertEqual(
            first_installment.matched_credit_ids.credit_move_id.move_id, other_payment
        )
        self._assert_unreconciled_message_posted(payment_order)

    def test_cancel_payment_order(self):
        invoice_company_a = self._create_intercompany_customer_invoice()
        payment_order = self._pay_invoice(
            invoice_company_a, self.payment_mode_company_a
        )
        auto_move = payment_order.payment_ids.auto_move_id
        payment_order.action_cancel()
        self.assertEqual(auto_move.state, "cancel")
        self.assertEqual(self.invoice_company_b.amount_residual, 450.0)
        payment_order.cancel2draft()
        self.assertFalse(auto_move.exists())
        payment_order.draft2open()
        self.assertFalse(payment_order.payment_ids.auto_move_id)

    def test_outstanding_account_from_chart_template(self):
        self.payment_mode_company_a.payment_account_id = False
        self.env["ir.model.data"].create(
            {
                "module": "account",
                "name": f"{self.company_a.id}_account_journal_payment_debit_account_id",
                "model": "account.account",
                "res_id": self.outstanding_account_company_a.id,
            }
        )
        invoice_company_b = self._create_intercompany_supplier_invoice()
        payment_order = self._pay_invoice(
            invoice_company_b, self.payment_mode_company_b
        )
        self.assertIn(
            self.outstanding_account_company_a,
            payment_order.payment_ids.auto_move_id.line_ids.account_id,
        )

    def test_missing_outstanding_account(self):
        self.payment_mode_company_a.payment_account_id = False
        invoice_company_b = self._create_intercompany_supplier_invoice()
        with self.assertRaisesRegex(UserError, "outstanding"):
            self._pay_invoice(invoice_company_b, self.payment_mode_company_b)

    def test_linked_invoice_of_another_company_left_unreconciled(self):
        paid_invoice = self._create_intercompany_supplier_invoice()
        linked_invoice = self.invoice_company_a
        paid_invoice.sudo().auto_invoice_id = self.invoice_company_b
        payment_order = self._pay_invoice(paid_invoice, self.payment_mode_company_b)
        self._assert_reconciled(paid_invoice)
        self.assertFalse(linked_invoice.line_ids.matched_credit_ids)
        mirror_line = payment_order.payment_ids.auto_move_id.line_ids.filtered(
            lambda line: line.credit
        )
        self.assertEqual(
            mirror_line.account_id,
            self.partner_company_b.with_company(
                self.company_a
            ).property_account_receivable_id,
        )
        self.assertFalse(mirror_line.reconciled)
        self._assert_unreconciled_message_posted(payment_order)

    def test_missing_bank_journal(self):
        self.bank_journal_company_a.bank_account_id = False
        invoice_company_b = self._create_intercompany_supplier_invoice()
        with self.assertRaisesRegex(UserError, "No bank journal"):
            self._pay_invoice(invoice_company_b, self.payment_mode_company_b)

    def test_partner_without_company(self):
        supplier = self.env["res.partner"].create({"name": "External supplier"})
        supplier_bank = self.env["res.partner.bank"].create(
            {
                "acc_number": "FR7630006000011234567890189",
                "partner_id": supplier.id,
                "allow_out_payment": True,
            }
        )
        self.invoice_company_b.write(
            {"partner_id": supplier.id, "partner_bank_id": supplier_bank.id}
        )
        self.invoice_company_b.action_post()
        payment_order = self._pay_invoice(
            self.invoice_company_b, self.payment_mode_company_b
        )
        self._assert_reconciled(self.invoice_company_b)
        self.assertFalse(payment_order.payment_ids.auto_move_id)

    def test_upload_by_user_of_paying_company_only(self):
        self.user_company_b.groups_id = [
            Command.link(
                self.env.ref("account_payment_batch_oca.group_account_payment").id
            )
        ]
        invoice_company_b = self._create_intercompany_supplier_invoice()
        payment_order = self._pay_invoice(
            invoice_company_b, self.payment_mode_company_b, self.user_company_b
        )
        self._assert_reconciled(self.invoice_company_a)
        self.assertEqual(
            payment_order.sudo().payment_ids.auto_move_id.company_id, self.company_a
        )
