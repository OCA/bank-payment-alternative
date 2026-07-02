# Copyright 2024 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import base64
import logging

from odoo import api, models
from odoo.exceptions import UserError
from odoo.modules.registry import Registry

_logger = logging.getLogger(__name__)


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    def _get_storage(self):
        if self.env.company.fs_storage_source_payment == "method_line":
            return self.payment_method_line_id.storage
        elif self.env.company.fs_storage_source_payment == "method":
            return self.payment_method_id.storage
        return ""

    def _must_be_exported_to_storage(self):
        self.ensure_one()
        return bool(self._get_storage())

    def _export_to_storage(self, file_content, filename):
        storage_id = int(self._get_storage())
        export_storage = self.env["fs.storage"].sudo().browse([storage_id])
        try:
            storage = export_storage._get_filesystem()
            storage.pipe_file(filename, file_content)
        except Exception as e:
            details = str(e) or str(type(e))
            _logger.error(details)
            raise UserError(
                self.env._(
                    "Unknown issue to upload the file on the storage:\n{details}",
                    details=details,
                )
            ) from e
        return True

    def _get_payment_attachment_to_export(self):
        self.ensure_one()
        return self.payment_file_id

    def open2generated(self):
        self.ensure_one()
        action = super().open2generated()
        if self._must_be_exported_to_storage():
            self.generated2uploaded()

            @self.env.cr.postcommit.add
            def export_attachment():
                db_registry = Registry(self.env.cr.dbname)
                with db_registry.cursor() as cr:
                    context = self.env.context
                    uid = self.env.uid
                    env = api.Environment(cr, uid, context)
                    order = self.with_env(env)
                    try:
                        attachment = order._get_payment_attachment_to_export()
                        if not attachment:
                            raise UserError(
                                self.env._("Attachment to upload not found!")
                            )
                        content = base64.b64decode(attachment.datas)
                        order._export_to_storage(content, attachment.name)
                    except UserError:
                        self.action_cancel()
                        self.message_post(
                            body=self.env._(
                                "Order set to canceled due to Error "
                                "while uploading file"
                            )
                        )

            action = {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "success",
                    "title": self.env._("Generate and export"),
                    "message": self.env._(
                        "The file has been scheduled to be dropped on the storage."
                    ),
                    "sticky": True,
                    "next": {
                        "type": "ir.actions.client",
                        "tag": "reload",
                    },
                },
            }
        return action
