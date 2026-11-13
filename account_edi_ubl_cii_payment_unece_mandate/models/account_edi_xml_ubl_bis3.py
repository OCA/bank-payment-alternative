# Copyright 2026  Akretion (https://www.akretion.com).
# @author Sébastien Alix <sebastien.alix@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models

import odoo.addons.account_edi_ubl_cii.tools.ubl_21_common as cac

# Update nodes template
cac.PaymentMeans.update(
    {
        "cac:PaymentMandate": {
            "cbc:ID": {},
            "cac:PayerFinancialAccount": {
                "cbc:ID": {},
            },
        },
    },
)


class AccountEdiXmlUBLBIS3(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"

    def _ubl_add_payment_means_nodes(self, vals):
        res = super()._ubl_add_payment_means_nodes(vals)
        nodes = vals["document_node"]["cac:PaymentMeans"]
        invoice = vals.get("invoice")
        if not invoice:
            return res
        if not invoice.mandate_id.partner_bank_id.acc_number:
            return res
        payment_method_line = invoice.preferred_payment_method_line_id
        payment_method = payment_method_line.payment_method_id
        if payment_method.unece_id:
            for node in nodes:
                # Add mandate if payment means is (SEPA) direct debit
                #   - 49: Direct Debit
                #   - 59: SEPA Direct Debit
                if node.get("cbc:PaymentMeansCode", {}).get("_text") not in (
                    "49",
                    "59",
                ):
                    continue
                node["cac:PaymentMandate"] = {
                    "cbc:ID": {
                        "_text": invoice.mandate_id.unique_mandate_reference,
                    },
                    "cac:PayerFinancialAccount": {
                        "cbc:ID": {
                            "_text": invoice.mandate_id.partner_bank_id.acc_number,
                        },
                    },
                }
                break
        return res
