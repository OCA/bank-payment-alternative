# Copyright 2026  Akretion (https://www.akretion.com).
# @author Sébastien Alix <sebastien.alix@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import base64

import lxml

from .common import CommonAccountEdiUneceMandate


class TestAccountEdiCII(CommonAccountEdiUneceMandate):
    def test_export_facturx(self):
        """Test export of UNECE payment mean mandate to FacturX XML file."""
        # Configure company
        self.env.company.write(
            {
                "country_id": self.env.ref("base.fr").id,
                "vat": "FR00000000000",
            }
        )
        # Configure partner
        self.partner.write(
            {
                "country_id": self.env.ref("base.fr").id,
                "invoice_edi_format": "facturx",
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
        #   <SpecifiedTradeSettlementPaymentMeans>
        payment_means = root.find(".//{*}SpecifiedTradeSettlementPaymentMeans")
        self.assertIsNotNone(payment_means)
        #       <MandateID>
        mandate_id = payment_means.find("{*}MandateID")
        self.assertIsNotNone(mandate_id)
        self.assertEqual(mandate_id.text, self.mandate.unique_mandate_reference)
        #       <PayerPartyDebtorFinancialAccount>
        payer_account = payment_means.find("{*}PayerPartyDebtorFinancialAccount")
        self.assertIsNotNone(payer_account)
        #           <IBANID> or <ProprietaryID>
        iban_id = payer_account.find("{*}IBANID")
        proprietary_id = payer_account.find("{*}ProprietaryID")
        self.assertTrue(iban_id is not None or proprietary_id is not None)
        if iban_id is not None:
            self.assertEqual(iban_id.text, self.partner_bank.acc_number)
