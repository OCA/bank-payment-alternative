Integrate payment mandates (module `account_payment_mandate` from
[OCA/bank-payment-alternative](https://github.com/OCA/bank-payment-alternative/))
with Odoo standard UBL electronic invoices (module `account_edi_ubl_cii`).

It is based on UNECE Payment Means (module `account_edi_ubl_cii_payment_unece`
from [OCA/edi](https://github.com/OCA/edi/) to automatically add a payment mandate
if the payment is typed as "Direct Debit".
