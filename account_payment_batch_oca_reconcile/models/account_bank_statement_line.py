# Copyright 2024 Dixmit
# Copyright 2025 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import re
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    # add_payment_lot_id is a technical field used by the bank statement reconcile
    # interface: when the user clicks on a payment lot, the onchange of this field is
    # called.
    add_payment_lot_id = fields.Many2one(
        "account.payment.lot",
        check_company=True,
        prefetch=False,
    )
    # technical fields used for filtering
    rejected_payment_min_date = fields.Date(compute="_compute_rejected_payment_infos")
    rejected_payment_min_amount = fields.Monetary(
        compute="_compute_rejected_payment_infos"
    )
    rejected_payment_max_amount = fields.Monetary(
        compute="_compute_rejected_payment_infos"
    )

    def _rejected_payment_max_delay_days(self):
        """This method is designed to be inherited"""
        # max rejection delay for SEPA direct debit is 13 months,
        # so I propose to set it to 14 months.
        # If you have a payment method that can have rejects after an even longer
        # delay, you should inherit this method
        return 366 + 2 * 31

    @api.depends("date", "amount", "currency_id")
    def _compute_rejected_payment_infos(self):
        max_days = self._rejected_payment_max_delay_days()
        for line in self:
            line.rejected_payment_min_date = (
                line.date and line.date - timedelta(max_days) or False
            )
            cur_rounding = line.currency_id.rounding
            pay_amount = abs(line.amount)
            line.rejected_payment_min_amount = pay_amount - cur_rounding
            line.rejected_payment_max_amount = pay_amount + cur_rounding

    def clean_reconcile(self):
        """
        Remove the counterparts when cleaning
        """
        res = super().clean_reconcile()
        self.reconcile_data_info["payment_lot_counterparts"] = []
        return res

    @api.onchange("add_payment_lot_id")
    def _onchange_add_payment_lot_id(self):
        """
        We need to check if the payment order is in already on the counterpart.
        In this case we need to add all the liquidity lines. Otherwise, we remove them
        """
        if self.add_payment_lot_id:
            self._add_payment_lot(self.add_payment_lot_id)
            self.add_payment_lot_id = False

    def _add_payment_lot(self, lot):
        new_data = []
        if lot.id not in self.reconcile_data_info.get("payment_lot_counterparts", []):
            # The user has selected a lot that has not already been selected
            counterpart_lines = []
            for line in self.reconcile_data_info["data"]:
                counterpart_lines += line.get("counterpart_line_ids", [])
                new_data.append(line)
            candidate_move_lines = lot._get_move_lines_to_reconcile()

            for line in candidate_move_lines.filtered(
                lambda r: r.id not in counterpart_lines
            ):
                reconcile_auxiliary_id, lines = self._get_reconcile_line(
                    line, "other", True, 0.0
                )
                new_data += lines

            data_info = self._recompute_suspense_line(
                new_data,
                self.reconcile_data_info["reconcile_auxiliary_id"],
                self.manual_reference,
            )
            data_info["payment_lot_counterparts"].append(lot.id)
        else:
            # The user selected a lot that has already been selected
            # for that statement line
            move_lines = lot._get_move_lines_to_reconcile()
            new_data = []
            for line in self.reconcile_data_info["data"]:
                if set(line.get("counterpart_line_ids", [])).intersection(
                    set(move_lines.ids)
                ):
                    continue
                new_data.append(line)
            data_info = self._recompute_suspense_line(
                new_data,
                self.reconcile_data_info["reconcile_auxiliary_id"],
                self.manual_reference,
            )
            lot_counterparts = set(data_info["payment_lot_counterparts"])
            lot_counterparts.remove(lot.id)
            data_info["payment_lot_counterparts"] = list(lot_counterparts)
        self.can_reconcile = data_info.get("can_reconcile", False)
        self.reconcile_data_info = data_info

    def _recompute_suspense_line(self, data, reconcile_auxiliary_id, manual_reference):
        """
        We want to keep the counterpart when we recompute
        """
        result = super()._recompute_suspense_line(
            data, reconcile_auxiliary_id, manual_reference
        )
        payment_lot_counterparts = (
            self.reconcile_data_info
            and self.reconcile_data_info.get("payment_lot_counterparts", [])
        ) or []
        result["payment_lot_counterparts"] = payment_lot_counterparts
        return result

    def add_multiple_lines(self, domain):
        """Method called by the button 'Add all'"""
        if ["state", "=", "uploaded"] in domain:
            # called from the "Payment lots" tab
            lots = self.env["account.payment.lot"].search(domain)
            for lot in lots:
                self._add_payment_lot(lot)
        else:
            # called from the "Reconcile" tab
            return super().add_multiple_lines(domain)

    # for rejection wizard
    def _get_rejection_info(self):
        self.ensure_one()
        fc = self.currency_id.compare_amounts(self.amount, 0)
        if fc > 0:
            payment_type = "outbound"
        elif fc < 0:
            payment_type = "inbound"
        else:
            raise UserError(
                self.env._(
                    "The amount of the bank statement line %s is zero.",
                    self.display_name,
                )
            )
        seq2pay_method_line = self._rejection_info_payment_sequences(payment_type)
        company_id = self.company_id.id
        payment_domain = [
            ("company_id", "=", company_id),
            ("journal_id", "=", self.journal_id.id),
            ("payment_type", "=", payment_type),
            ("currency_id", "=", self.currency_id.id),
            ("state", "in", ("paid", "in_process")),
            ("payment_order_id", "!=", False),
            ("date", "<=", self.date),
            ("date", ">=", self.rejected_payment_min_date),
            ("payment_reference", "!=", False),
        ]
        payment = False
        partner_id = False
        match_method = False
        for seq, payment_method_line in seq2pay_method_line.items():
            assert seq.prefix
            _logger.info("Working on sequence ID %s with code %s", seq.id, seq.code)
            prefix = re.escape(seq.prefix)
            padding = seq.padding
            pattern = f"{prefix}\d{{{padding},{padding + 1}}}/LOT\d{{1,2}}/\d{{1,5}}"
            res_find = re.findall(pattern, self.payment_ref)
            _logger.debug("res_find=%s", res_find)
            if res_find:
                if len(res_find) > 1:
                    _logger.info(
                        "Several matches on payment sequence found: %s. "
                        "Using the first one",
                        res_find,
                    )
                payment_memo_extracted = res_find[0]
                _logger.debug("payment_memo_extracted=%s", payment_memo_extracted)
                additional_pay_domain = [("memo", "=", payment_memo_extracted)]
                if (
                    payment_method_line
                    and payment_method_line.bank_account_link == "fixed"
                ):
                    additional_pay_domain.append(
                        ("payment_method_line_id", "=", payment_method_line.id)
                    )
                payments = self.env["account.payment"].search(
                    payment_domain + additional_pay_domain, order="date desc"
                )
                for pay in payments:
                    if not self.currency_id.compare_amounts(
                        abs(self.amount), pay.amount
                    ):
                        payment = pay
                        break
                if payment:
                    break
        if payment:
            match_method = "endtoend_id"
            partner_id = payment.partner_id.id
        elif self.partner_id:
            additional_pay_domain = [
                ("partner_id", "=", self.partner_id.id),
                ("memo", "!=", False),
                ("amount", "<=", self.rejected_payment_max_amount),
                ("amount", ">=", self.rejected_payment_min_amount),
            ]
            payments = self.env["account.payment"].search(
                payment_domain + additional_pay_domain, order="date desc"
            )
            payment, match_method = self._rejection_filter_payment_by_amount(payments)
            partner_id = self.partner_id.id
        else:
            match_method = "no_partner_no_match"

        payment_id = payment and payment.id or False
        return payment_type, payment_id, partner_id, match_method

    def _rejection_filter_payment_by_amount(self, payments):
        if not payments:
            return (False, "partner_no_match")
        pay_st_line_amount = abs(self.amount)
        currency = self.currency_id
        st_line_label_upper = self.payment_ref and self.payment_ref.upper()
        last_payment_match = False
        for payment in payments:
            if not currency.compare_amounts(pay_st_line_amount, payment.amount):
                if not last_payment_match:
                    last_payment_match = payment
                if payment.payment_reference.upper() in st_line_label_upper:
                    return (payment, "remittance_info")
        if last_payment_match:
            return (last_payment_match, "partner_last")
        return (False, "partner_no_match")

    def _rejection_info_payment_sequences(self, payment_type):
        self.ensure_one()
        company_id = self.company_id.id
        # get sequences specific to a payment method
        seq2pay_method_line = {}
        pay_method_lines = self.env["account.payment.method.line"].search(
            [
                ("company_id", "=", company_id),
                ("payment_type", "=", payment_type),
                ("payment_order_ok", "=", True),
                ("selectable", "=", True),
                ("specific_sequence_id", "!=", False),
                "|",
                ("journal_id", "=", self.journal_id.id),
                ("variable_journal_ids", "in", self.journal_id.id),
            ]
        )
        for pay_method_line in pay_method_lines:
            seq = pay_method_line.specific_sequence_id
            if not seq.prefix:
                raise UserError(
                    self.env._(
                        "Sequence '%(seq)s' configured on the payment method "
                        "'%(pay_method_line)s' doesn't have a prefix.",
                        seq=seq.display_name,
                        pay_method_line=pay_method_line.display_name,
                    )
                )
            if "%(" in seq.prefix and ")s" in seq.prefix:
                raise UserError(
                    self.env._(
                        "Sequence '%(seq)s' configured on the payment method "
                        "'%(pay_method_line)s' has a dynamic prefix '%(prefix)s'. "
                        "Only fixed prefixes are supported for the moment.",
                        seq=seq.display_name,
                        pay_method_line=pay_method_line.display_name,
                        prefix=seq.prefix,
                    )
                )
            seq2pay_method_line[seq] = pay_method_line
        # get the generic payment sequences
        payment_type2seq_code = {
            "inbound": "account.payment.order.inbound",
            "outbound": "account.payment.order",
        }
        std_sequences = self.env["ir.sequence"].search(
            [
                ("code", "=", payment_type2seq_code[payment_type]),
                ("company_id", "in", [company_id, False]),
            ],
            order="company_id",
        )
        for seq in std_sequences:
            if not seq.prefix:
                raise UserError(
                    self.env._(
                        "Sequence '%(seq)s' for payment/debit orders "
                        "doesn't have a prefix.",
                        seq=seq.display_name,
                    )
                )
            if "%(" in seq.prefix and ")s" in seq.prefix:
                raise UserError(
                    self.env._(
                        "Sequence '%(seq)s' for payment/debit orders has a dynamic "
                        "prefix '%(prefix)s'. Only fixed prefixes are supported "
                        "for the moment.",
                        seq=seq.display_name,
                        prefix=seq.prefix,
                    )
                )
            seq2pay_method_line[seq] = None
        _logger.debug("seq2pay_method_line: %s", seq2pay_method_line)
        if not seq2pay_method_line:
            raise UserError(
                self.env._(
                    "No sequence detected for payment/debit orders in company %s. "
                    "This should never happen.",
                    self.company_id.display_name,
                )
            )
        return seq2pay_method_line
