#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    env.cr.execute("""
        ALTER TABLE account_payment_method_line
        ADD column old_payment_mode_id int,
        ADD COLUMN old_refund_payment_mode_id int
    """)
    env.cr.execute("""
        SELECT id,
               name,
               company_id,
               payment_method_id,
               fixed_journal_id as journal_id,
               bank_account_link,
               create_date,
               create_uid,
               write_date,
               write_uid,
               show_bank_account,
               refund_payment_mode_id,
               active
        from account_payment_mode
    """)
    payment_mode_info = env.cr.dictfetchall()
    for params in payment_mode_info:
        params["name"] = json.dumps(params["name"])
        params["selectable"] = True
        mode_id = params.pop("id")
        refund_mode_id = params.pop("refund_payment_mode_id")
        params["old_payment_mode_id"] = mode_id
        params["old_refund_payment_mode_id"] = refund_mode_id
        method_id = env.cr.execute(
            """insert into account_payment_method_line (
            name,
            payment_method_id,
            bank_account_link,
            journal_id,
            selectable,
            company_id,
            create_uid,
            create_date,
            write_uid,
            write_date,
            show_bank_account,
            old_payment_mode_id,
            old_refund_payment_mode_id,
            active
        )
        values (
            %(name)s,
            %(payment_method_id)s,
            %(bank_account_link)s,
            %(journal_id)s,
            %(selectable)s,
            %(company_id)s,
            %(create_uid)s,
            %(create_date)s,
            %(write_uid)s,
            %(write_date)s,
            %(show_bank_account)s,
            %(old_payment_mode_id)s,
            %(old_refund_payment_mode_id)s,
            %(active)s
        ) RETURNING id
        """,
            params,
        )
        # get variable journals
        env.cr.execute(
            """
            SELECT rel.journal_id
            FROM account_payment_mode m
            JOIN account_payment_mode_variable_journal_rel rel
            ON rel.payment_mode_id = %s
            WHERE bank_account_link = 'variable'
        """,
            (method_id,),
        )
        journal_ids = [x[0] for x in env.cr.fetchall()]
        if journal_ids:
            env["account.payment.method.line"].browse(method_id).write(
                {"variable_journal_ids": journal_ids}
            )

    env.cr.execute("""
        UPDATE account_payment_method_line
        SET refund_payment_method_line_id = apml2.id
        FROM account_payment_method_line apml2
        WHERE account_payment_method_line.old_refund_payment_mode_id IS NOT NULL
        AND account_payment_method_line.old_refund_payment_mode_id = apml2.old_payment_mode_id
    """)  # noqa: E501
    # TODO migrate supplier_payment_mode_id and customer_payment_mode_id
    env.cr.execute("""
        UPDATE account_move
        SET preferred_payment_method_line_id = apml.id
        FROM account_payment_mode apm, account_payment_method_line apml
        WHERE account_move.payment_mode_id = apm.id
        AND apm.id = apml.old_payment_mode_id
        AND account_move.preferred_payment_method_line_id IS NULL
    """)
