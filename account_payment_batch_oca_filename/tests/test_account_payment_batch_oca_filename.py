# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import tagged

from odoo.addons.account_payment_batch_oca.tests.test_payment_order_outbound import (
    TestPaymentOrderOutboundBase,
)


@tagged("-at_install", "post_install")
class TestAccountPaymentBatchOcaFilename(TestPaymentOrderOutboundBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.order = cls.env["account.payment.order"].create(
            {
                "payment_type": "outbound",
                "payment_method_line_id": cls.creation_mode.id,
            }
        )

        cls.sequence_payment_order = cls.env["ir.sequence"].create(
            {
                "name": "Test sequence pay",
                "code": "test.custom.sequence",
                "prefix": "",
                "padding": 2,
                "number_next": 1,
                "number_increment": 1,
                "company_id": False,
            }
        )

    def test_computation_filename(self):
        """Test computation of filename with and without custom sequence"""
        filename = self.order._prepare_filename()
        self.assertEqual(filename, self.order.name)
        self.order.payment_method_line_id.filename_sequence_id = (
            self.sequence_payment_order
        )

        # The sequence hasn't been generated yet therefore, it will be 01
        next_sequence = "01"

        filename = self.order._prepare_filename()
        self.assertEqual(filename, next_sequence)
