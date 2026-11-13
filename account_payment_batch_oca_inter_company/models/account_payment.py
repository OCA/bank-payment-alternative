# Copyright 2022 Akretion France (https://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
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
            dest_company = payment.payment_line_ids._get_inter_company()
            if not dest_company:
                continue
            dest_payment = payment.sudo().with_company(dest_company)
            bank_journal = dest_payment._get_inter_company_bank_journal(dest_company)
            payment.auto_move_id = dest_payment._create_inter_company_move(bank_journal)

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
        return {
            "partner_id": self.company_id.partner_id.id,
            "name": self.payment_reference,
            "account_id": self._get_inter_company_outstanding_account(bank_journal).id,
            "balance": -self.payment_line_ids._get_mirror_sign() * self.amount,
        }

    def _prepare_inter_company_move_vals(self, bank_journal):
        self.ensure_one()
        return {
            "move_type": "entry",
            "journal_id": bank_journal.id,
            "company_id": bank_journal.company_id.id,
            "date": self.date,
            "ref": self.memo,
        }

    def _create_inter_company_move(self, bank_journal):
        self.ensure_one()
        return self.payment_line_ids._create_mirror_move(
            bank_journal.company_id,
            self._prepare_inter_company_move_vals(bank_journal),
            [self._prepare_move_line_pending_account(bank_journal)],
        )
