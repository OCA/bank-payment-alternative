Add the receivables to net to a supplier payment order: the amount of their
payment line is negative, and can be lowered to net only part of the residual.

On confirmation, the order is refused if the net amount of a transfer group is
negative, even when the partner's total over all its bank accounts is positive.

Limits:

- A line with a structured reference cannot be netted: the bank file would
  carry the reference of a single invoice for a net amount.
- The module does not check the legal conditions of netting (insolvency
  proceedings, public creditors, consumers, ...): the accountant remains
  responsible for the receivables they net.
