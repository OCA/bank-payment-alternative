# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Account Payment Batch OCA Inter Company Netting",
    "summary": "Inter-company payment entry of netted payment orders",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Akretion,Odoo Community Association (OCA)",
    "development_status": "Beta",
    "website": "https://github.com/OCA/bank-payment-alternative",
    "category": "Banking addons",
    "depends": [
        "account_payment_batch_oca_inter_company",
        "account_payment_batch_oca_netting",
    ],
    "data": ["views/res_config_settings_views.xml"],
    "auto_install": True,
    "installable": True,
}
