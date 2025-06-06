# Copyright 2010-2020 Akretion (www.akretion.com)
# Copyright 2014-2022 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from lxml import objectify

from odoo import _, models
from odoo.exceptions import UserError


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def generate_payment_file(self):
        """Creates the SEPA Credit Transfer file. That's the important code!"""
        self.ensure_one()
        if self.payment_method_id.code != "sepa_credit_transfer":
            return super().generate_payment_file()

        pain_flavor = self.payment_method_id.pain_version
        # We use pain_flavor.startswith('pain.001.001.xx')
        # to support country-specific extensions such as
        # pain.001.001.03.ch.02 (cf l10n_ch_sepa)
        if not pain_flavor:
            raise UserError(_("PAIN version '%s' is not supported.") % pain_flavor)
        elif pain_flavor.startswith(("pain.001.001.03", "pain.001.003.03")):
            bic_xml_tag = "BIC"
            # size 70 -> 140 for <Nm> with pain.001.001.03
            # BUT the European Payment Council, in the document
            # "SEPA Credit Transfer Scheme Customer-to-bank
            # Implementation guidelines" v6.0 available on
            # http://www.europeanpaymentscouncil.eu/knowledge_bank.cfm
            # says that 'Nm' should be limited to 70
            # so we follow the "European Payment Council"
            # and we put 70 and not 140
            name_maxsize = 70
        elif pain_flavor.startswith("pain.001.001.09"):
            bic_xml_tag = "BICFI"
            name_maxsize = 140
        # added pain.001.003.03 for German Banks
        # it is not in the offical ISO 20022 documentations, but nearly all
        # german banks are working with this instead 001.001.03
        else:
            raise UserError(_("PAIN version '%s' is not supported.") % pain_flavor)
        xsd_file = self.payment_method_id._get_xsd_file_path()
        gen_args = {
            "bic_xml_tag": bic_xml_tag,
            "name_maxsize": name_maxsize,
            "convert_to_ascii": self._convert_to_ascii(),
            "payment_method": "TRF",
            "pain_flavor": pain_flavor,
            "pain_xsd_file": xsd_file,
            "date_fmt": "%Y-%m-%d",
        }
        nsmap = self._generate_pain_nsmap()
        attrib = self._generate_pain_attrib()
        xml_root = objectify.Element("Document", nsmap=nsmap, attrib=attrib)
        pain_root = objectify.SubElement(xml_root, "CstmrCdtTrfInitn")
        # A. Group header
        group_header = self._generate_group_header_block(pain_root, gen_args)
        transactions_count_a = 0
        amount_control_sum_a = 0.0
        # key = (requested_date, priority, local_instrument, categ_purpose)
        # values = list of lines as object
        for lot in self.payment_lot_ids:
            # B. Payment info
            payment_info = lot._generate_start_payment_info_block(pain_root, gen_args)
            self._generate_party_block(
                payment_info, "Dbtr", "B", self.company_partner_bank_id, gen_args
            )
            self._generate_charge_bearer(payment_info)
            for line in lot.payment_ids:
                # C. Credit Transfer Transaction Info
                transactions_count_a += 1
                credit_transfer_transaction_info = objectify.SubElement(
                    payment_info, "CdtTrfTxInf"
                )
                payment_identification = objectify.SubElement(
                    credit_transfer_transaction_info, "PmtId"
                )
                payment_identification.InstrId = self._prepare_field(
                    "Instruction Identification",
                    line.memo or str(line.id),
                    35,
                    gen_args,
                )
                payment_identification.EndToEndId = self._prepare_field(
                    "End to End Identification", line.memo or str(line.id), 35, gen_args
                )
                amount = objectify.SubElement(credit_transfer_transaction_info, "Amt")
                amount.InstdAmt = line.currency_id._pain_format(line.amount)
                amount.InstdAmt.set("Ccy", line.currency_id.name)
                amount_control_sum_a += line.amount
                if not line.partner_bank_id:
                    raise UserError(
                        _(
                            "Bank account is missing on the bank payment line "
                            "of partner '{partner}' (reference '{reference}')."
                        ).format(partner=line.partner_id.name, reference=line.name)
                    )

                self._generate_party_block(
                    credit_transfer_transaction_info,
                    "Cdtr",
                    "C",
                    line.partner_bank_id,
                    gen_args,
                    line,
                )
                payment_line = line.payment_line_ids[0]
                payment_line._generate_purpose(credit_transfer_transaction_info)
                payment_line._generate_regulatory_reporting(
                    credit_transfer_transaction_info, gen_args
                )
                self._generate_remittance_info_block(
                    credit_transfer_transaction_info, line, gen_args
                )
        group_header.NbOfTxs = str(transactions_count_a)
        group_header.CtrlSum = self._format_control_sum(amount_control_sum_a)
        return self._finalize_sepa_file_creation(xml_root, gen_args)
