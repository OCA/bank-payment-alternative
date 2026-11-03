# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, fields

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class NettingCommon(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.env.user.groups_id = [
            Command.link(
                cls.env.ref("account_payment_batch_oca.group_account_payment").id
            )
        ]
        cls.company = cls.company_data["company"]
        cls.payable_account = cls.company_data["default_account_payable"]
        cls.receivable_account = cls.company_data["default_account_receivable"]
        cls.partner = cls.env["res.partner"].create({"name": "Netting Partner"})
        cls.bank_a, cls.bank_b = cls.env["res.partner.bank"].create(
            [
                {
                    "acc_number": acc_number,
                    "partner_id": cls.partner.id,
                    "allow_out_payment": True,
                }
                for acc_number in ("FR7600001", "FR7600002")
            ]
        )
        payment_method = (
            cls.env["account.payment.method"]
            .sudo()
            .create(
                {
                    "name": "Netting test transfer",
                    "code": "test_manual",
                    "payment_type": "outbound",
                    "payment_order_ok": True,
                    "bank_account_required": True,
                }
            )
        )
        cls.company_data["default_journal_bank"].bank_account_id = cls.env[
            "res.partner.bank"
        ].create(
            {
                "acc_number": "FR7600003",
                "partner_id": cls.company.partner_id.id,
            }
        )
        cls.outstanding_account = cls.env["account.account"].create(
            {
                "name": "Outgoing payments",
                "code": "511820",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        cls.netting_mode = cls.env["account.payment.method.line"].create(
            {
                "name": "Netting transfer",
                "payment_account_id": cls.outstanding_account.id,
                "company_id": cls.company.id,
                "journal_id": cls.company_data["default_journal_bank"].id,
                "payment_method_id": payment_method.id,
                "selectable": True,
                "group_lines": True,
                "netting": True,
            }
        )

    @classmethod
    def _create_invoice(
        cls, move_type, amount, partner=None, date_due=None, open_account=None
    ):
        account = (
            cls.company_data["default_account_expense"]
            if move_type in ("in_invoice", "in_refund")
            else cls.company_data["default_account_revenue"]
        )
        invoice = cls.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": (partner or cls.partner).id,
                "invoice_date": fields.Date.today(),
                "ref": f"{move_type} {amount}",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": f"{move_type} line",
                            "quantity": 1,
                            "price_unit": amount,
                            "account_id": account.id,
                            "tax_ids": [Command.clear()],
                        }
                    )
                ],
            }
        )
        if date_due:
            invoice.invoice_date_due = date_due
        if open_account:
            cls._open_line(invoice).account_id = open_account
        invoice.action_post()
        return invoice

    @classmethod
    def _create_debit_entry(cls, account, amount, partner=None):
        entry = cls.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": cls.company_data["default_journal_misc"].id,
                "ref": f"Debit {amount}",
                "line_ids": [
                    Command.create(
                        {
                            "name": "Debit",
                            "account_id": account.id,
                            "partner_id": (partner or cls.partner).id,
                            "debit": amount,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Counterpart",
                            "account_id": cls.company_data[
                                "default_account_revenue"
                            ].id,
                            "credit": amount,
                        }
                    ),
                ],
            }
        )
        entry.action_post()
        return entry

    @classmethod
    def _open_line(cls, move):
        return move.line_ids.filtered(
            lambda line: line.account_id.reconcile and line.partner_id
        )

    def _create_order(self, move_lines, mode=None):
        order = self.env["account.payment.order"].create(
            {
                "payment_type": "outbound",
                "payment_method_line_id": (mode or self.netting_mode).id,
            }
        )
        move_lines.create_payment_line_from_move_line(order)
        return order

    def _confirm(self, order):
        order.draft2open()
        return order

    def _upload(self, order):
        if order.state == "draft":
            order.draft2open()
        order.open2generated()
        order.generated2uploaded()
        return order
