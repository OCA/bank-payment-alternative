# Copyright 2026  Akretion (https://www.akretion.com).
# @author Sébastien Alix <sebastien.alix@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo.addons.account_edi_ubl_cii_payment_unece.tests.common import (
    CommonAccountEdiUnece,
)


class CommonAccountEdiUneceMandate(CommonAccountEdiUnece):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Configure payment method for SEPA direct debit (UNECE code 59)
        unece = cls.env.ref("account_payment_unece.payment_means_59")
        cls.inbound_payment_method.unece_id = unece
        cls.inbound_payment_method.mandate_required = True
        # Create a res.partner.bank record with mandate on self.partner
        cls.partner_bank = cls.env["res.partner.bank"].create(
            {
                "partner_id": cls.partner.id,
                "acc_number": "BE82068997597303",
            }
        )
        cls.mandate = cls.env["account.banking.mandate"].create(
            {
                "partner_id": cls.partner.id,
                "partner_bank_id": cls.partner_bank.id,
                "unique_mandate_reference": "MANDATE123",
                "signature_date": "2024-01-01",
                "state": "valid",
            }
        )
