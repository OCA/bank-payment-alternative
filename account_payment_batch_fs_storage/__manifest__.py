# Copyright 2024 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Account Payment Batch Fs Storage",
    "summary": """
        Add the possibility to specify on the payment method or on the
        payment method line depending on the company,
        a storage where files generated will be pushed to upon payment
    """,
    "version": "19.0.1.0.0",
    "license": "AGPL-3",
    "author": "ACSONE SA/NV,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/bank-payment-alternative",
    "depends": [
        "account_payment_sepa_credit_transfer",
        "account_payment_base_oca",
        "fs_storage",
    ],
    "data": [
        "security/res_groups.xml",
        "security/fs_storage.xml",
        "views/res_config_settings.xml",
        "views/account_payment_method_line.xml",
        "views/account_payment_method.xml",
    ],
    "demo": [],
}
