This module adds netting to outbound payment orders: receivables of a partner
(customer invoices, supplier refunds, debit miscellaneous entries on any
reconcilable account) are added to a supplier payment order as negative lines,
so that only the net amount is transferred.

For each transfer group (partner, bank account, currency), the payment entry has
one liquidity line for the net amount and one counterpart line per payment line,
on the account of its journal item. On upload, each counterpart line is
reconciled with its journal item, partially if the payment line amount is lower
than the residual. Receivable and payable balances stay gross.
