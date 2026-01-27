# Copyright 2024 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from lxml import objectify

from odoo import models

logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _generate_address_block(self, parent_node, gen_args):
        """Generate the piece of the XML corresponding to address block
        Following EPC guidelines:
        https://www.europeanpaymentscouncil.eu/document-library/guidance-documents/
        guidance-use-structured-addresses-2025-sepa-payment-schemes
        Apart from PAIN flavors that only support the unstructured address format,
        we use the hybrid format because it is the most appropriate for the native
        Odoo datamodel (allowed since October 5th 2025)
        """
        self.ensure_one()
        if gen_args["pain_flavor"].startswith(("pain.001.003.03", "pain.008.003.02")):
            # only for german-specific PAIN variants
            return self._generate_unstructured_address_block(parent_node, gen_args)
        apoo = self.env["account.payment.order"]
        if self.country_id:
            postal_address = objectify.SubElement(parent_node, "PstlAdr")
            if self.zip:
                postal_address.PstCd = apoo._prepare_field(
                    "ZIP Code", self.zip, 16, gen_args
                )
            if self.city:
                postal_address.TwnNm = apoo._prepare_field(
                    "City", self.city, 35, gen_args
                )
            if self.state_id:
                postal_address.CtrySubDvsn = apoo._prepare_field(
                    "State", self.state_id.name, 35, gen_args
                )
            postal_address.Ctry = self.country_id.code
            if self.street:
                postal_address.AdrLine = apoo._prepare_field(
                    "Street as Address Line 1", self.street, 70, gen_args
                )
            if self.street2:
                postal_address.AdrLine = apoo._prepare_field(
                    "Street2 as Address Line 2", self.street2, 70, gen_args
                )

    def _generate_unstructured_address_block(self, parent_node, gen_args):
        """Generation of unstructured address block is deprecated according to EPC
        and will not be allowed after nov 2025
        But the german variant pain.001.003.03 still requires it
        """
        apoo = self.env["account.payment.order"]
        if self.country_id:
            postal_address = objectify.SubElement(parent_node, "PstlAdr")
            postal_address.Ctry = self.country_id.code
            street_list = [self.street, self.street2]
            street = " - ".join([entry for entry in street_list if entry])
            if street:
                postal_address.AdrLine = apoo._prepare_field(
                    "Street as Address Line 1", street, 70, gen_args
                )
            zipcity_list = [self.zip, self.city]
            zipcity = " ".join([entry for entry in zipcity_list if entry])
            if zipcity:
                postal_address.AdrLine = apoo._prepare_field(
                    "Zip and City as Address Line 2", zipcity, 70, gen_args
                )

    def _generate_party_id(self, parent_node, party_type):
        """Generate an Id element for partner inside the parent node.
        party_type can currently be Cdtr or Dbtr. Notably, the initiating
        party orgid is generated with another mechanism and configured
        at the company or payment method level.
        """
        self.ensure_one()
        return
