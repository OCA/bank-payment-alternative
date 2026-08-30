# Copyright 2026  Akretion (https://www.akretion.com).
# @author Sébastien Alix <sebastien.alix@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import base64

import lxml

from .common import CommonAccountEdiUneceMandate


class TestAccountEdiUBLBIS3(CommonAccountEdiUneceMandate):
    def test_export_ubl_bis3(self):
        """Test export of UNECE payment mean mandate to BIS3 XML file."""
        # Configure partner
        self.partner.write(
            {
                "country_id": self.env.ref("base.be").id,
                "invoice_edi_format": "ubl_bis3",
            }
        )
        # Create invoice
        invoice = self._create_out_invoice(post=True)
        self.assertTrue(invoice.preferred_payment_method_line_id)
        # Send it to generate its XML file
        wiz_send = (
            self.env["account.move.send.wizard"]
            .with_context(active_model=invoice._name, active_ids=invoice.ids)
            .create({})
        )
        wiz_send.action_send_and_print()
        # Check XML file content
        self.assertTrue(invoice.ubl_cii_xml_file)
        xml = base64.b64decode(invoice.ubl_cii_xml_file)
        root = lxml.etree.fromstring(xml)
        #   <cac:PaymentMeans>
        payment_means = root.find(".//{*}PaymentMeans")
        self.assertTrue(len(payment_means))
        #       <cac:PaymentMandate>
        payment_mandate = payment_means.find("{*}PaymentMandate")
        self.assertIsNotNone(payment_mandate)
        #           <cbc:ID>
        payment_mandate_ref = payment_mandate.find("{*}ID")
        self.assertEqual(
            payment_mandate_ref.text, self.mandate.unique_mandate_reference
        )
        #           <cac:PayerFinancialAccount>
        payment_mandate_account = payment_mandate.find("{*}PayerFinancialAccount")
        self.assertIsNotNone(payment_mandate_account)
        #               <cbc:ID>
        payment_mandate_account_ref = payment_mandate_account.find("{*}ID")
        self.assertEqual(payment_mandate_account_ref.text, self.partner_bank.acc_number)
