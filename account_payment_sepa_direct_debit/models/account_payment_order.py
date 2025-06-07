# Copyright 2020 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# Copyright 2018-2022 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import objectify

from odoo import _, models
from odoo.exceptions import UserError


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def generate_payment_file(self):
        """Creates the SEPA Direct Debit file. That's the important code !"""
        self.ensure_one()
        if self.payment_method_id.code != "sepa_direct_debit":
            return super().generate_payment_file()
        pain_flavor = self.payment_method_id.pain_version
        # We use pain_flavor.startswith('pain.008.001.xx')
        # to support country-specific extensions such as
        # pain.008.001.02.ch.01 (cf l10n_ch_sepa)
        if pain_flavor.startswith(("pain.008.001.02", "pain.008.003.02")):
            bic_xml_tag = "BIC"
            name_maxsize = 70
        elif pain_flavor.startswith("pain.008.001.08"):
            bic_xml_tag = "BICFI"
            name_maxsize = 140
        else:
            raise UserError(_("PAIN version '%s' is not supported.") % pain_flavor)
        pay_method = self.payment_method_id
        xsd_file = pay_method._get_xsd_file_path()
        gen_args = {
            "bic_xml_tag": bic_xml_tag,
            "name_maxsize": name_maxsize,
            "convert_to_ascii": self._convert_to_ascii(),
            "payment_method": "DD",
            "pain_flavor": pain_flavor,
            "pain_xsd_file": xsd_file,
            "date_fmt": "%Y-%m-%d",
        }
        nsmap = self._generate_pain_nsmap()
        attrib = self._generate_pain_attrib()
        xml_root = objectify.Element("Document", nsmap=nsmap, attrib=attrib)
        pain_root = objectify.SubElement(xml_root, "CstmrDrctDbtInitn")
        # A. Group header
        group_header = self._generate_group_header_block(pain_root, gen_args)
        transactions_count_a = 0
        amount_control_sum_a = 0.0
        for lot in self.payment_lot_ids:
            # B. Payment info
            payment_info = lot._generate_start_payment_info_block(pain_root, gen_args)
            self._generate_party_block(
                payment_info, "Cdtr", "B", self.company_partner_bank_id, gen_args
            )
            self._generate_charge_bearer(payment_info)
            sepa_creditor_identifier = (
                self.payment_method_line_id.sepa_creditor_identifier
                or self.company_id.sepa_creditor_identifier
            )
            if not sepa_creditor_identifier:
                raise UserError(
                    _(
                        "Missing SEPA Creditor Identifier on company %(company)s "
                        "(or on payment mode %(payment_mode)s).",
                        company=self.company_id.display_name,
                        payment_mode=self.payment_method_line_id.display_name,
                    )
                )
            self._generate_creditor_scheme_identification(
                payment_info,
                sepa_creditor_identifier,
                "SEPA Creditor Identifier",
                "SEPA",
                gen_args,
            )
            for line in lot.payment_ids:
                # C. Direct Debit Transaction Info
                transactions_count_a += 1
                dd_transaction_info = objectify.SubElement(payment_info, "DrctDbtTxInf")
                payment_identification = objectify.SubElement(
                    dd_transaction_info, "PmtId"
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
                dd_transaction_info.InstdAmt = line.currency_id._pain_format(
                    line.amount
                )
                dd_transaction_info.InstdAmt.set("Ccy", line.currency_id.name)
                amount_control_sum_a += line.amount
                dd_transaction = objectify.SubElement(dd_transaction_info, "DrctDbtTx")
                mandate_related_info = objectify.SubElement(
                    dd_transaction, "MndtRltdInf"
                )
                mandate = line.payment_line_ids[:1].mandate_id
                mandate_related_info.MndtId = self._prepare_field(
                    "Unique Mandate Reference",
                    mandate.unique_mandate_reference,
                    35,
                    gen_args,
                    raise_if_oversized=True,
                )
                mandate_related_info.DtOfSgntr = mandate.signature_date.strftime(
                    gen_args["date_fmt"]
                )
                if lot.sequence_type == "FRST" and mandate.last_debit_date:
                    mandate_related_info.AmdmntInd = "true"
                    amendment_info_details = objectify.SubElement(
                        mandate_related_info, "AmdmntInfDtls"
                    )
                    ori_debtor_account = objectify.SubElement(
                        amendment_info_details, "OrgnlDbtrAcct"
                    )
                    ori_debtor_account_id = objectify.SubElement(
                        ori_debtor_account, "Id"
                    )
                    ori_debtor_agent_other = objectify.SubElement(
                        ori_debtor_account_id, "Othr"
                    )
                    ori_debtor_agent_other.Id = "SMNDA"
                    # Until 20/11/2016, SMNDA meant
                    # "Same Mandate New Debtor Agent"
                    # After 20/11/2016, SMNDA means
                    # "Same Mandate New Debtor Account"

                self._generate_party_block(
                    dd_transaction_info,
                    "Dbtr",
                    "C",
                    line.partner_bank_id,
                    gen_args,
                    line,
                )
                payment_line = line.payment_line_ids[0]
                payment_line._generate_purpose(dd_transaction_info)
                payment_line._generate_regulatory_reporting(
                    dd_transaction_info, gen_args
                )
                self._generate_remittance_info_block(
                    dd_transaction_info, line, gen_args
                )

        group_header.NbOfTxs = str(transactions_count_a)
        group_header.CtrlSum = self._format_control_sum(amount_control_sum_a)
        return self._finalize_sepa_file_creation(xml_root, gen_args)

    def generated2uploaded(self):
        """Write 'last debit date' on mandates
        Set oneoff mandates and recurring/final mandates to expired
        """
        res = super().generated2uploaded()
        abmo = self.env["account.banking.mandate"]
        for order in self:
            if order.payment_method_id.mandate_required:
                to_expire_mandates = abmo
                all_mandates = abmo
                for line in order.payment_line_ids:
                    mandate = line.mandate_id
                    if mandate in all_mandates:
                        continue
                    all_mandates |= mandate
                    if mandate.type == "oneoff":
                        to_expire_mandates |= mandate
                    elif mandate.type == "recurrent" and mandate.state == "final":
                        to_expire_mandates |= mandate
                # We use order.date_generated and not today because users often
                # forget to do generated2uploaded after successful upload
                # on the bank, and they do the generated2uploaded later on
                all_mandates.write({"last_debit_date": order.date_generated})
                to_expire_mandates.write({"state": "expired"})
        return res
