# Copyright 2026  Akretion (https://www.akretion.com).
# @author Sébastien Alix <sebastien.alix@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
{
    "name": "Electronic invoices with UBL/CII - UNECE payments with mandates",
    "version": "18.0.1.0.0",
    "category": "Accounting & Finance",
    "license": "AGPL-3",
    "summary": "Add mandates with UNECE payments in UBL and CII XML documents.",
    "author": "BCIM, Akretion, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/bank-payment-alternative",
    "depends": [
        # OCA/edi
        "account_edi_ubl_cii_payment_unece",
        # OCA/bank-payment-alternative
        "account_payment_mandate",
    ],
    "data": [
        "data/ubl_20_templates.xml",
    ],
    "installable": True,
    "auto_install": True,
}
