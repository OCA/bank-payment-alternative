def migrate(cr, version):
    cr.execute(
        """
        UPDATE account_payment_method_line AS method_line
        SET order_uploaded_mail_template_id = model_data.res_id
        FROM ir_model_data AS model_data
        WHERE model_data.module = 'account_payment_batch_oca'
            AND model_data.name = 'payment_order_mail_notif'
            AND model_data.model = 'mail.template'
            AND method_line.order_uploaded_mail_template_id IS NULL
        """
    )
