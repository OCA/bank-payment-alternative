# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Account Payment Batch OCA Netting",
    "summary": "Net receivables against payables in payment orders",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Akretion,Odoo Community Association (OCA)",
    "development_status": "Beta",
    "website": "https://github.com/OCA/bank-payment-alternative",
    "category": "Banking addons",
    "depends": ["account_payment_batch_oca"],
    "data": [
        "views/account_payment_method_line.xml",
        "views/account_payment_order.xml",
    ],
    "installable": True,
}
