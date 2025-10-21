#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from openupgradelib import openupgrade

from odoo.fields import first


@openupgrade.migrate()
def migrate(env, version):
    env.cr.execute("""
        UPDATE account_payment_method
        SET payment_order_ok = payment_order_only
    """)
    env.cr.execute("""
        UPDATE account_payment_method_line
        SET payment_order_ok = apm.payment_order_ok,
            no_debit_before_maturity = apm.no_debit_before_maturity,
            default_payment_mode = apm.default_payment_mode,
            default_invoice = apm.default_invoice,
            default_target_move = apm.default_target_move,
            default_date_type = apm.default_date_type,
            default_date_prefered = apm.default_date_prefered,
            group_lines = apm.group_lines
        FROM account_payment_mode apm
        WHERE account_payment_method_line.old_payment_mode_id IS NOT NULL
        AND apm.id = account_payment_method_line.old_payment_mode_id
    """)
    # manage default_journal_ids
    # remove default computed values
    env.cr.execute("DELETE FROM account_journal_account_payment_mode_rel")
    # fill from old payment mode table
    env.cr.execute("""
        INSERT INTO account_journal_account_payment_method_line_rel
            (account_payment_method_line_id, account_journal_id)
        SELECT
            t2.id,
            t1.account_journal_id
        FROM
            account_journal_account_payment_mode_rel AS t1
        JOIN
            account_payment_method_line AS t2
            ON t1.account_payment_mode_id = t2.old_payment_mode_id;
    """)

    env.cr.execute("""
        UPDATE account_payment_order
        SET payment_method_line_id = apml.id,
            payment_method_code = account_payment_method.code
        FROM account_payment_method_line apml,
             account_payment_mode apm,
             account_payment_method
        WHERE account_payment_order.payment_mode_id = apm.id
        AND apml.old_payment_mode_id = apm.id
        AND account_payment_method.id = apml.payment_method_id
    """)

    # generate lot for confirmed payment orders
    for order in env["account.payment.order"].search([("state", "=", "open")]):
        lots = {}
        for payment in order.payment_ids:
            payment_line = first(payment.payment_line_ids)
            if not payment_line:
                continue
            lot_key = payment_line._lot_grouping_key()
            if lot_key not in lots:
                lots[lot_key] = env["account.payment.lot"].create(
                    payment_line._prepare_account_payment_lot_vals(len(lot_key) + 1)
                )
            payment.write({"payment_lot_id": lots[lot_key].id})
