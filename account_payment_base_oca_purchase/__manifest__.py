# Copyright 2026 Scalizer (https://www.scalizer.fr)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Payment Base OCA - Purchase",
    "version": "19.0.1.0.0",
    "category": "Banking addons",
    "license": "AGPL-3",
    "summary": "Adds payment method on purchase orders",
    "author": "Scalizer, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/bank-payment-alternative",
    "depends": ["purchase", "account_payment_base_oca"],
    "data": [
        "views/purchase_order_views.xml",
    ],
    "auto_install": True,
}
