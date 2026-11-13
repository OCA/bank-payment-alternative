import logging

from odoo import fields, models
from odoo.addons.queue_job.delay import group

logger = logging.getLogger(__name__)


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def generated2uploaded(self):
        self.ensure_one()
        method_line = self.payment_method_line_id
        mail_notif = method_line.mail_notif
        unposted_payment_ids = self.payment_ids.filtered(lambda r: r.state != "posted")
        queue = group(
            *[
                self.delayable()._post_and_reconcile_payments(payment_id, mail_notif)
                for payment_id in unposted_payment_ids
            ]
        )
        if mail_notif:
            queue.on_done(self.delayable()._send_mail_notif(self.payment_ids))
        queue.on_done(
            self.delayable().write(
                {"state": "uploaded", "date_uploaded": fields.Date.context_today(self)}
            )
        ).delay()

    def action_cancel(self):
        chains = []
        for payment_id in self.payment_ids:
            chains.append(
                payment_id.delayable()
                .action_draft()
                .on_done(payment_id.delayable().action_cancel())
            )
        payment_group = group(*chains)

        if self.payment_file_id:
            payment_group.on_done(self.payment_file_id.delayable().unlink())

        payment_group.on_done(
            self.delayable().write(
                {
                    "state": "cancel",
                    "date_generated": False,
                }
            )
        ).delay()
