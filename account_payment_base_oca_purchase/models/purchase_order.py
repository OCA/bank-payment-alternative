# Copyright 2026 Scalizer (https://www.scalizer.fr)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    preferred_payment_method_line_id = fields.Many2one(
        comodel_name="account.payment.method.line",
        string="Payment Method",
        compute="_compute_preferred_payment_method_line_id",
        store=True,
        readonly=False,
        precompute=True,
        check_company=True,
        domain="[('payment_type', '=', 'outbound'), ('company_id', '=', company_id), "
        "('selectable', '=', True)]",
    )

    @api.depends("partner_id", "company_id")
    def _compute_preferred_payment_method_line_id(self):
        """Take the outbound payment method of the vendor, in the order company."""
        for order in self:
            partner = order.partner_id.with_company(order.company_id)
            order.preferred_payment_method_line_id = (
                partner.property_outbound_payment_method_line_id
            )

    def _prepare_invoice(self):
        """Give the payment method of the order to the vendor bill."""
        invoice_vals = super()._prepare_invoice()
        if self.preferred_payment_method_line_id:
            invoice_vals["preferred_payment_method_line_id"] = (
                self.preferred_payment_method_line_id.id
            )
        return invoice_vals
