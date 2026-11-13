In *Invoicing \> Configuration \> Settings*, section *Default Accounts*,
set the reconcilable inter-company dividend accounts:

- *Receivable* on the company paying the transfer. If it is not set, no
  line is a dividend: its mirror goes on the partner's payable account;
- *Payable* on the company receiving it. Uploading a payment order with
  a netted dividend is refused if this account is not set.

In the same section, set the *Inter-company netting journal* (general
journal) on the company receiving the transfers. Uploading a payment
order with a net-zero group for that company is refused if it is not
set.
