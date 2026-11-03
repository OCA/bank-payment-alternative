# Copyright 2022 Akretion France (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, _, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    auto_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Inter Company Payment Entry",
        readonly=True,
        copy=False,
    )

    def unlink(self):
        self.sudo().with_context(force_delete=True).auto_move_id.unlink()
        return super().unlink()

    def action_draft(self):
        result = super().action_draft()
        self.sudo().auto_move_id.filtered(
            lambda move: move.state == "posted"
        ).button_draft()
        return result

    def action_cancel(self):
        result = super().action_cancel()
        self.sudo().auto_move_id.filtered(
            lambda move: move.state in ("draft", "posted")
        ).button_cancel()
        return result

    def _reconcile_inter_company_invoices(self):
        for payment in self:
            dest_company = payment._get_inter_company()
            if not dest_company:
                continue
            dest_payment = payment.sudo().with_company(dest_company)
            bank_journal = dest_payment._get_inter_company_bank_journal(dest_company)
            payment.auto_move_id = dest_payment._create_inter_company_move(bank_journal)

    def _get_inter_company(self):
        self.ensure_one()
        return (
            self.env["res.company"]
            .sudo()
            .search(
                [
                    ("partner_id", "=", self.partner_id.commercial_partner_id.id),
                    ("id", "!=", self.company_id.id),
                ],
                limit=1,
            )
        )

    def _get_inter_company_bank_journal(self, dest_company):
        self.ensure_one()
        bank_journal = self.env["account.journal"].search(
            [
                ("company_id", "=", dest_company.id),
                ("type", "=", "bank"),
                (
                    "bank_account_id.sanitized_acc_number",
                    "=",
                    self.partner_bank_id.sanitized_acc_number,
                ),
            ],
            limit=1,
        )
        if not bank_journal:
            raise UserError(
                _(
                    "No bank journal found for the bank account"
                    " %(account_number)s in the company %(company_name)s",
                    account_number=self.partner_bank_id.sanitized_acc_number,
                    company_name=dest_company.name,
                )
            )
        return bank_journal

    def _get_inter_company_outstanding_account(self, bank_journal):
        self.ensure_one()
        if self.payment_type == "outbound":
            method_lines = bank_journal.inbound_payment_method_line_ids
            account_ref = "account_journal_payment_debit_account_id"
        else:
            method_lines = bank_journal.outbound_payment_method_line_ids
            account_ref = "account_journal_payment_credit_account_id"
        account = method_lines.payment_account_id[:1]
        if not account:
            account = (
                self.env["account.chart.template"]
                .with_company(bank_journal.company_id)
                .ref(account_ref, raise_if_not_found=False)
            )
        if not account:
            raise UserError(
                _(
                    "No outstanding account found on the bank journal %(journal)s"
                    " of the company %(company_name)s.",
                    journal=bank_journal.display_name,
                    company_name=bank_journal.company_id.name,
                )
            )
        return account

    def _prepare_move_line_pending_account(self, bank_journal):
        self.ensure_one()
        sign = -1 if self.payment_type == "outbound" else 1
        return {
            "partner_id": self.company_id.partner_id.id,
            "name": self.payment_reference,
            "account_id": self._get_inter_company_outstanding_account(bank_journal).id,
            "balance": -sign * self.amount,
        }

    def _prepare_move_line_invoice(self, payment_line, dest_invoice, dest_company):
        self.ensure_one()
        if dest_invoice:
            partner = dest_invoice.commercial_partner_id
            if dest_invoice.state == "draft":
                name = dest_invoice.ref
            else:
                name = dest_invoice.name
        else:
            partner = self.company_id.partner_id
            name = payment_line.communication
        partner = partner.with_company(dest_company)
        if self.payment_type == "outbound":
            account = partner.property_account_receivable_id
            sign = -1
        else:
            account = partner.property_account_payable_id
            sign = 1
        return {
            "partner_id": partner.id,
            "name": name,
            "account_id": account.id,
            "balance": sign * payment_line.amount_currency,
        }

    def _get_dest_invoice(self, payment_line, dest_company):
        orig_invoice = payment_line.move_line_id.move_id
        if orig_invoice.auto_generated:
            return orig_invoice.auto_invoice_id
        else:
            return self.env["account.move"].search(
                [
                    ("auto_invoice_id", "=", orig_invoice.id),
                    ("company_id", "=", dest_company.id),
                ],
                limit=1,
            )

    def _prepare_inter_company_move_vals(self, bank_journal, line_vals_list):
        self.ensure_one()
        return {
            "move_type": "entry",
            "journal_id": bank_journal.id,
            "company_id": bank_journal.company_id.id,
            "date": self.date,
            "ref": self.memo,
            "line_ids": [Command.create(vals) for vals in line_vals_list],
        }

    def _create_inter_company_move(self, bank_journal):
        self.ensure_one()
        dest_company = bank_journal.company_id
        dest_invoices = [
            self._get_dest_invoice(payment_line, dest_company)
            for payment_line in self.payment_line_ids
        ]
        line_vals_list = [
            self._prepare_move_line_invoice(payment_line, dest_invoice, dest_company)
            for payment_line, dest_invoice in zip(
                self.payment_line_ids, dest_invoices, strict=True
            )
        ] + [self._prepare_move_line_pending_account(bank_journal)]
        move = (
            self.env["account.move"]
            .with_company(dest_company)
            .create(self._prepare_inter_company_move_vals(bank_journal, line_vals_list))
        )
        move.action_post()
        invoice_lines = move.line_ids.sorted("id")[:-1]
        self._reconcile_inter_company_lines(
            zip(invoice_lines, dest_invoices, strict=True)
        )
        return move

    def _reconcile_inter_company_lines(self, line_invoice_pairs):
        for line, dest_invoice in line_invoice_pairs:
            dest_invoice_line = dest_invoice.line_ids.filtered(
                lambda aml: aml.account_id.account_type
                in ("asset_receivable", "liability_payable")
            )
            if not dest_invoice_line or dest_invoice.state == "draft":
                continue
            (line | dest_invoice_line[0]).reconcile()
