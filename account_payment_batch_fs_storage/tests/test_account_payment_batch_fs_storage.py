# Copyright 2024 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from contextlib import contextmanager
from datetime import date
from unittest.mock import patch

from odoo import _
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("-at_install", "post_install")
class TestAccountPaymentBatchFsStorage(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.company_data["company"]
        cls.company_data_2 = cls.setup_other_company()
        cls.other_company = cls.company_data_2["company"]
        cls.env.user.group_ids |= cls.env.ref(
            "account_payment_batch_oca.group_account_payment"
        )

        cls.fs_storage_method = cls.env["fs.storage"].create(
            {"name": "Test storage method", "code": "test_method", "protocol": "odoofs"}
        )
        cls.fs_storage_method_line = cls.env["fs.storage"].create(
            {
                "name": "Test storage method line",
                "code": "test_method_line",
                "protocol": "odoofs",
            }
        )

        cls.payment_method = cls.env.ref(
            "account.account_payment_method_manual_out"
        ).sudo().copy(
            {
                "name": "method test",
                "code": "test",
            }
        )

        cls.bank_journal = cls.company_data["default_journal_bank"]
        cls.bank_journal2 = cls.company_data_2["default_journal_bank"]

        cls.payment_method_line = cls.env["account.payment.method.line"].create(
            {
                "name": "Test method line",
                "payment_method_id": cls.payment_method.id,
                "bank_account_link": "fixed",
                "journal_id": cls.bank_journal.id,
            }
        )
        cls.payment_method_line2 = cls.env["account.payment.method.line"].create(
            {
                "name": "Test method line 2",
                "payment_method_id": cls.payment_method.id,
                "bank_account_link": "fixed",
                "journal_id": cls.bank_journal2.id,
            }
        )

        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})

    @contextmanager
    def with_custom_method(self):
        path = (
            "odoo.addons.account_payment_batch_oca.models"
            ".account_payment_order.AccountPaymentOrder.generate_payment_file"
        )
        with patch(
            path,
            new=lambda self: (b"Content", "Filename"),
            create=not hasattr(
                self.env["account.payment.order"], "generate_payment_file"
            ),
        ):
            yield

    @contextmanager
    def with_raise_error_while_exporting(self):
        def dummy_raise():
            raise UserError(_("Error"))

        path = (
            "odoo.addons.account_payment_batch_fs_storage.models"
            ".account_payment_order.AccountPaymentOrder._export_to_storage"
        )
        with patch(path, new=dummy_raise, create=True):
            yield

    def _make_order(self, method_line, journal):
        order = self.env["account.payment.order"].create(
            {
                "payment_type": "outbound",
                "payment_method_line_id": method_line.id,
                "journal_id": journal.id,
            }
        )
        self.env["account.payment.line"].create(
            {
                "order_id": order.id,
                "partner_id": self.partner.id,
                "communication": "test",
                "currency_id": journal.company_id.currency_id.id,
                "amount_currency": 200,
                "date": date.today(),
            }
        )
        return order

    def test_payment_method_fs_storage(self):
        self.env.user.company_id = self.company.id
        self.company.fs_storage_source_payment = "method"
        self.env["ir.config_parameter"].sudo().set_param(
            f"account_payment_batch_fs_storage.fs_storage_ids_{self.company.id}",
            [self.fs_storage_method.id],
        )
        self.payment_method.storage = str(self.fs_storage_method.id)

        order = self._make_order(self.payment_method_line, self.bank_journal)
        order.draft2open()
        with self.with_custom_method():
            action = order.open2generated()

        self.assertDictEqual(
            action,
            {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "success",
                    "title": "Generate and export",
                    "message": "The file has been scheduled to be dropped on the storage.",
                    "sticky": True,
                    "next": {"type": "ir.actions.client", "tag": "reload"},
                },
            },
        )
        self.assertTrue(order.payment_file_id)
        self.assertEqual(order.state, "uploaded")

    def test_check_use_on_payment_method(self):
        self.env.user.company_id = self.company.id
        self.company.fs_storage_source_payment = "method"
        method_config = self.env["res.config.settings"].create({})
        method_config.fs_storage_source_payment = "method"
        method_config.fs_storage_ids = [self.fs_storage_method.id]
        self.env["ir.config_parameter"].sudo().set_param(
            f"account_payment_batch_fs_storage.fs_storage_ids_{self.company.id}",
            [self.fs_storage_method.id],
        )

        self.payment_method.storage = str(self.fs_storage_method.id)
        self.assertEqual(self.payment_method.storage, str(self.fs_storage_method.id))

        with self.assertRaisesRegex(
            UserError, "Storage is already used on at least one payment method"
        ):
            method_config.fs_storage_ids = False

        self.payment_method.write({"storage": False})
        method_config.fs_storage_ids = False

    def test_method_fs_storage_other_company(self):
        self.env.user.company_id = self.other_company.id
        self.other_company.fs_storage_source_payment = "method"
        self.env["ir.config_parameter"].sudo().set_param(
            f"account_payment_batch_fs_storage.fs_storage_ids_{self.other_company.id}",
            [self.fs_storage_method.id],
        )
        self.payment_method.storage = str(self.fs_storage_method.id)

        order = self._make_order(self.payment_method_line2, self.bank_journal2)
        order.draft2open()
        with self.with_custom_method():
            action = order.open2generated()

        self.assertDictEqual(
            action,
            {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "success",
                    "title": "Generate and export",
                    "message": "The file has been scheduled to be dropped on the storage.",
                    "sticky": True,
                    "next": {"type": "ir.actions.client", "tag": "reload"},
                },
            },
        )
        self.assertTrue(order.payment_file_id)
        self.assertEqual(order.state, "uploaded")

    def test_payment_method_line_fs_storage(self):
        self.env.user.company_id = self.company.id
        self.company.fs_storage_source_payment = "method_line"
        self.env["ir.config_parameter"].sudo().set_param(
            f"account_payment_batch_fs_storage.fs_storage_ids_{self.company.id}",
            [self.fs_storage_method_line.id],
        )
        self.payment_method_line.storage = str(self.fs_storage_method_line.id)

        order = self._make_order(self.payment_method_line, self.bank_journal)
        order.draft2open()
        with self.with_custom_method():
            action = order.open2generated()

        self.assertDictEqual(
            action,
            {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "success",
                    "title": "Generate and export",
                    "message": "The file has been scheduled to be dropped on the storage.",
                    "sticky": True,
                    "next": {"type": "ir.actions.client", "tag": "reload"},
                },
            },
        )
        self.assertTrue(order.payment_file_id)
        self.assertEqual(order.state, "uploaded")

    def test_check_use_on_payment_method_line(self):
        self.env.user.company_id = self.company.id
        self.company.fs_storage_source_payment = "method_line"
        line_config = self.env["res.config.settings"].create({})
        line_config.fs_storage_source_payment = "method_line"
        line_config.fs_storage_ids = [self.fs_storage_method_line.id]
        self.env["ir.config_parameter"].sudo().set_param(
            f"account_payment_batch_fs_storage.fs_storage_ids_{self.company.id}",
            [self.fs_storage_method_line.id],
        )

        self.payment_method_line.storage = str(self.fs_storage_method_line.id)
        self.assertEqual(
            self.payment_method_line.storage, str(self.fs_storage_method_line.id)
        )

        with self.assertRaisesRegex(
            UserError, "Storage is already used on at least one payment method_line"
        ):
            line_config.fs_storage_ids = False

        self.payment_method_line.write({"storage": False})
        line_config.fs_storage_ids = False

    def test_error_while_uploading(self):
        self.env.user.company_id = self.company.id
        self.company.fs_storage_source_payment = "method_line"
        self.env["ir.config_parameter"].sudo().set_param(
            f"account_payment_batch_fs_storage.fs_storage_ids_{self.company.id}",
            [self.fs_storage_method_line.id],
        )
        self.payment_method_line.storage = str(self.fs_storage_method_line.id)

        order = self._make_order(self.payment_method_line, self.bank_journal)
        order.draft2open()
        with self.with_custom_method():
            order.open2generated()

        with self.with_raise_error_while_exporting():
            self.env.cr.postcommit.run()

        self.assertEqual(order.state, "cancel")
