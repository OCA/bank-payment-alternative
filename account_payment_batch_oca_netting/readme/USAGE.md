Add the receivables to net to a supplier payment order: the amount of their
payment line is negative, and can be lowered to net only part of the residual.

On a netting payment method line, the "Create Transactions" wizard has an
"Include receivables" option, checked by default: it also proposes the
unreconciled debit journal items of the partners that have a payable in the
order or in the selection, with the same date, target moves, partner and
invoice filters as payables. The journals and payment method filters apply to
payables only, as receivables usually come from sale or miscellaneous journals.
Journal items of payments and bank statement lines, and journal items on a
liquidity account of the bank journal, are not proposed.

A line that does not come from a vendor bill takes the bank account of a vendor
bill line of the same partner in the order, so that it falls into the same
transfer group; without such a line, the partner's first bank account.

On confirmation, the order is refused if the net amount of a transfer group is
negative, even when the partner's total over all its bank accounts is positive.

A negative line must be linked to a debit journal item of its partner, not on a
liquidity account of the bank journal, and the lines of the order on this journal
item cannot exceed its residual. These conditions are checked again on
confirmation and on upload.

A transfer group whose net amount is zero gives no payment and is absent from
the bank file. On upload, a miscellaneous entry is posted instead, in the bank
journal of the order at the payment date, with the same counterpart lines as a
payment entry and no liquidity line; each line is reconciled with its journal
item. Cancelling the order cancels this entry, as it does for payments. An order
made only of such groups generates no bank file.

Limits:

- A line with a structured reference cannot be netted: the bank file would
  carry the reference of a single invoice for a net amount.
- The module does not check the legal conditions of netting (insolvency
  proceedings, public creditors, consumers, ...): the accountant remains
  responsible for the receivables they net.
