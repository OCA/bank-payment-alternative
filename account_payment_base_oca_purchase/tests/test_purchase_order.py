# Copyright 2026 Scalizer (https://www.scalizer.fr)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import Form, tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestPurchaseOrder(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Test bank",
                "code": "TBNK",
                "type": "bank",
                "company_id": cls.company.id,
            }
        )
        manual_out = cls.env.ref("account.account_payment_method_manual_out")
        cls.method_line = cls.env["account.payment.method.line"].create(
            {
                "name": "Test transfer",
                "payment_method_id": manual_out.id,
                "bank_account_link": "fixed",
                "journal_id": cls.journal.id,
                "selectable": True,
            }
        )
        cls.method_line_2 = cls.env["account.payment.method.line"].create(
            {
                "name": "Test check",
                "payment_method_id": manual_out.id,
                "bank_account_link": "fixed",
                "journal_id": cls.journal.id,
                "selectable": True,
            }
        )
        cls.vendor = cls.env["res.partner"].create(
            {
                "name": "Test vendor",
                "property_outbound_payment_method_line_id": cls.method_line.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Test product", "type": "service", "purchase_method": "purchase"}
        )

    def _create_order(self, partner):
        with Form(self.env["purchase.order"]) as order_form:
            order_form.partner_id = partner
            with order_form.order_line.new() as line:
                line.product_id = self.product
                line.product_qty = 1
                line.price_unit = 100
        return order_form.save()

    def _create_bill(self, order):
        order.button_confirm()
        order.action_create_invoice()
        return order.invoice_ids

    def test_payment_method_from_vendor(self):
        order = self._create_order(self.vendor)
        self.assertEqual(order.preferred_payment_method_line_id, self.method_line)
        bill = self._create_bill(order)
        self.assertEqual(bill.preferred_payment_method_line_id, self.method_line)

    def test_payment_method_changed_on_order(self):
        order = self._create_order(self.vendor)
        order.preferred_payment_method_line_id = self.method_line_2
        bill = self._create_bill(order)
        self.assertEqual(bill.preferred_payment_method_line_id, self.method_line_2)

    def test_vendor_without_payment_method(self):
        vendor = self.env["res.partner"].create({"name": "Vendor without method"})
        order = self._create_order(vendor)
        self.assertFalse(order.preferred_payment_method_line_id)
        bill = self._create_bill(order)
        self.assertFalse(bill.preferred_payment_method_line_id)
