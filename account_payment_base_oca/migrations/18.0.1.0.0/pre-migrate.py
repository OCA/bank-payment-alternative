#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    env.cr.execute("""
        UPDATE ir_model_data
        SET noupdate = false
        WHERE module = 'account_payment_base_oca'
        AND name = 'view_account_invoice_report_search'
    """)
