# Copyright 2019 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPaymentLine(models.Model):
    _inherit = "account.payment.line"

    mandate_format = fields.Selection(
        related="mandate_id.format", string="Mandate Format"
    )
    mandate_type = fields.Selection(related="mandate_id.type", string="Mandate Type")
    mandate_state = fields.Selection(related="mandate_id.state", string="Mandate State")

    def _compute_sepa_final_hook(self, sepa):
        sepa = super()._compute_sepa_final_hook(sepa)
        if sepa and self.mandate_id:
            if self.mandate_id.format not in ("sepa_core", "sepa_b2b"):
                return False
            # another module may have added more values to 'type'
            if self.mandate_id.type not in ("oneoff", "recurrent"):
                return False
        return sepa

    def draft2open_payment_line_check(self):
        res = super().draft2open_payment_line_check()
        sepa_dd_lines = self.filtered(
            lambda line: line.order_id.payment_method_id.code == "sepa_direct_debit"
        )
        sepa_dd_lines._check_sepa_direct_debit_ready()
        return res

    def _check_sepa_direct_debit_ready(self):
        """
        This method checks whether the payment line(s) are ready to be used
        in the SEPA Direct Debit file generation.
        :raise: UserError if a line does not fulfils all requirements
        """
        for rec in self:
            if not rec.mandate_id:
                raise UserError(
                    _(
                        "Missing SEPA Direct Debit mandate on the line with "
                        "partner {partner_name} (reference {reference})."
                    ).format(partner_name=rec.partner_id.name, reference=rec.name)
                )
            if rec.mandate_id.state not in ("valid", "final"):
                raise UserError(
                    _(
                        "The SEPA Direct Debit mandate with reference "
                        "{mandate_ref} for partner {partner_name} has "
                        "expired."
                    ).format(
                        mandate_ref=rec.mandate_id.unique_mandate_reference,
                        partner_name=rec.partner_id.name,
                    )
                )
            if rec.mandate_id.type == "oneoff" and rec.mandate_id.last_debit_date:
                raise UserError(
                    _(
                        "The SEPA Direct Debit mandate with reference "
                        "{mandate_ref} for partner {partner_name} has type set "
                        "to 'One-Off' but has a last debit date set to "
                        "{last_debit_date}. Therefore, it cannot be used."
                    ).format(
                        mandate_ref=rec.mandate_id.unique_mandate_reference,
                        partner_name=rec.partner_id.name,
                        last_debit_date=rec.mandate_id.last_debit_date,
                    )
                )

    @api.model
    def _lot_grouping_fields(self):
        res = super()._lot_grouping_fields()
        # 'state' is used to separate sequence 'recurring' and sequence 'final'
        res += ["mandate_format", "mandate_type", "mandate_state"]
        return res

    def _prepare_account_payment_lot_vals(self, lot_sequence):
        """This method should only use fields listed in self._lot_grouping_fields()"""
        vals = super()._prepare_account_payment_lot_vals(lot_sequence)
        if (
            self.order_id.payment_method_id.code == "sepa_direct_debit"
            and self.order_id.sepa
        ):
            mandate = self.mandate_id
            assert mandate
            assert mandate.format.startswith("sepa_")
            format2local_instrument = {
                "sepa_core": "CORE",
                "sepa_b2b": "B2B",
            }
            vals["local_instrument"] = format2local_instrument[mandate.format]
            if mandate.type == "oneoff":
                vals["sequence_type"] = "OOFF"
            else:
                if mandate.state == "valid":
                    vals["sequence_type"] = "RCUR"
                elif mandate.state == "final":
                    vals["sequence_type"] = "FNAL"
                else:
                    raise UserError(
                        _("Mandate '%s' is not in state 'Valid' nor 'Final Debit'.")
                        % mandate.display_name
                    )
        return vals
