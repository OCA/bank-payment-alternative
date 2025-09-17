
[![Runboat](https://img.shields.io/badge/runboat-Try%20me-875A7B.png)](https://runboat.odoo-community.org/builds?repo=OCA/bank-payment-alternative&target_branch=18.0)
[![Pre-commit Status](https://github.com/OCA/bank-payment-alternative/actions/workflows/pre-commit.yml/badge.svg?branch=18.0)](https://github.com/OCA/bank-payment-alternative/actions/workflows/pre-commit.yml?query=branch%3A18.0)
[![Build Status](https://github.com/OCA/bank-payment-alternative/actions/workflows/test.yml/badge.svg?branch=18.0)](https://github.com/OCA/bank-payment-alternative/actions/workflows/test.yml?query=branch%3A18.0)
[![codecov](https://codecov.io/gh/OCA/bank-payment-alternative/branch/18.0/graph/badge.svg)](https://codecov.io/gh/OCA/bank-payment-alternative)
[![Translation Status](https://translation.odoo-community.org/widgets/bank-payment-alternative-18-0/-/svg-badge.svg)](https://translation.odoo-community.org/engage/bank-payment-alternative-18-0/?utm_source=widget)

<!-- /!\ do not modify above this line -->

# Bank Payment - Alternative approach based on Odoo native payment methods

This projet is, as its name suggests, an alternative to the [OCA bank-payment project](https://github.com/OCA/bank-payment).

In Odoo 18.0, three new fields were added in the **account** module: two fields on res.partner for *Customer Payment Method* and *Supplier Payment Method* and a field *Payment Method* on invoices. These 3 new fields are *many2one* fields that point to *account.payment.method.line*. These fields are redunant with the equivalent fields definied in the OCA module *account_payment_partner* of the project OCA/bank-payment that point to *account.payment.mode* which is defined in the OCA module *account_payment_mode* from OCA/bank-payment.

On 18.0, the project OCA/bank-payment continues to use the object *account.payment.mode* and, by default, hides the 3 equivalent fields of the **account** module that point to *account.payment.method.line*.

On the contrary, the project [OCA/bank-payment-alternative](https://github.com/OCA/bank-payment-alternative) made the changes in the code base to fully adopt the three new *Payment Method* fields added in the **account** module in Odoo 18.0.

In the project OCA/bank-payment-alternative, the modules had to be renamed. In the table below, you will find the correspondance between the modules names of OCA/bank-payment and OCA/bank-payment-alternative:

OCA/bank-payment | OCA/bank-payment-alternative
--- | ---
account_payment_mode | *native* + account_payment_base_oca
account_payment_partner | *native*
account_payment_sale | account_payment_base_oca_sale
account_payment_order | account_payment_batch_oca
account_payment_order_tier_validation | account_payment_batch_oca_tier_validation
account_banking_pain_base | account_payment_sepa_base
account_banking_sepa_credit_transfer | account_payment_sepa_credit_transfer
account_banking_mandate | account_payment_mandate
account_banking_mandate_sale | account_payment_mandate_sale
account_banking_sepa_direct_debit | account_payment_sepa_direct_debit

The project OCA/bank-payment-alternative also introduced several new features and improvements, listed below by order of importance :

* Introduce a new object for payment lots *account.payment.lot* which is used to ease the generation of SCT and SDD XML files. This object is also used in the bank statement reconcile interface, to make it easy for the user to reconcile bank statement lines that correspond to a payment lot (module account_payment_batch_oca_reconcile).
* Take into account the boolean field *allow_out_payment* of res.partner.bank on payment orders: when you try to confirm a payment order that has bank accounts on payment lines with *allow_out_payment = False*, the user gets a blocking error message. The affected payment lines will be shown in red and the user will have a smart button that gives access to the bank accounts that are not allowed to send money to. To enable *allow_out_payment*, the user needs to be part of a specific group *Validate bank accounts* (XMLID *account.group_validate_bank_account*). As a consequence, the native ACL of *res.partner.bank* that give full rights to partner manager is not inherited any more: the security is handled by the boolean field *allow_out_payment*.
* the datamodel of the mandate has been simplified: the field *format* also has the information of the *scheme* field, so *format* now has 3 possible values : *basic*, *sepa_core* or *sepa_b2b*. The field *scheme* has been removed. The field *type* has 2 possible values: *recurrent* or *oneoff* (instead of 3 possible values : *generic*, *recurrent* or *oneoff*). The field *recurrent_sequence_type* has been removed because we don't need to handle the *first* vs *recurring* sequence any more : since November 2016, *the requirement to use the sequence type 'First' in a first of a recurrent series of Collections is no longer mandatory* according to the [EPC](https://www.europeanpaymentscouncil.eu/), cf SDD Core Rulebook. The *final* sequence is now supported by the state field which has a new *final* state that can be activated via a button. The field *partner_id* is NOT a related field of *partner_bank_id* any more, which solves the bug [account_banking_mandate: Change in the filtering behavior of the "Bank Account" field](https://github.com/OCA/bank-payment/issues/1473). With all these simplifications on the mandate datamodel, the form view and list view of mandates are more user-friendly.
* by default, there is a sequence for payment orders and another sequence for debit orders. It is possible to configure a specific sequence for a payment method.
* add support for *Regulatory Reporting* in the SEPA XML structure (tag *RgltryRptg*). Needed in some countries for international non-SEPA credit transfers.
* replace unstructured address by structured address in SEPA XML file (mandatory starting november 2025 according to the EPC).
* add support for pain.008.01.08 (SDD) and pain.001.001.09 (SCT), which are now the recommended versions of the EPC.
* easier download of the banking file after generation.
* add field *acc_number_scrambled* on res.partner.bank for easy and direct use of scrambled account number.
* search on partner from payment/debit orders search view.
* support currencies with *decimal_places* != 2 in ISO20022 XML file generation
* on mandates, fields *format*, *type*, *signature date* and *partner* become readonly when the mandate is not in *draft* state
* remove support for pain.001.001.02/04/05 (SCT) and pain.008.01.03/04 (SDD) which have never been selected by the EPC, in order to simplify the code that generate the XML.
* stop using *safe_eval()* in XML generation.
* replace all @api.onchange by computed fields.
* add sql unicity constraint on payment order number per company.

<!-- /!\ do not modify below this line -->

<!-- prettier-ignore-start -->

[//]: # (addons)

Available addons
----------------
addon | version | maintainers | summary
--- | --- | --- | ---
[account_payment_base_oca](account_payment_base_oca/) | 18.0.1.5.0 | <a href='https://github.com/alexis-via'><img src='https://github.com/alexis-via.png' width='32' height='32' style='border-radius:50%;' alt='alexis-via'/></a> | OCA extensions to native payment objects of Odoo
[account_payment_base_oca_sale](account_payment_base_oca_sale/) | 18.0.2.0.0 |  | Adds payment method on sale orders
[account_payment_batch_oca](account_payment_batch_oca/) | 18.0.3.2.0 |  | Add payment orders and debit orders
[account_payment_batch_oca_reconcile](account_payment_batch_oca_reconcile/) | 18.0.1.0.0 | <a href='https://github.com/alexis-via'><img src='https://github.com/alexis-via.png' width='32' height='32' style='border-radius:50%;' alt='alexis-via'/></a> | Easy reconciliation of payment/debit lots on bank statement reconcile interface
[account_payment_batch_oca_tier_validation](account_payment_batch_oca_tier_validation/) | 18.0.1.0.0 | <a href='https://github.com/marcelsavegnago'><img src='https://github.com/marcelsavegnago.png' width='32' height='32' style='border-radius:50%;' alt='marcelsavegnago'/></a> | Tier validation process on payment/debit orders
[account_payment_mandate](account_payment_mandate/) | 18.0.2.0.0 |  | Add support for banking mandates used in direct debits
[account_payment_mandate_sale](account_payment_mandate_sale/) | 18.0.1.0.0 | <a href='https://github.com/alexis-via'><img src='https://github.com/alexis-via.png' width='32' height='32' style='border-radius:50%;' alt='alexis-via'/></a> | Adds mandates on sale orders
[account_payment_sepa_base](account_payment_sepa_base/) | 18.0.2.1.0 |  | Base module for SEPA file generation
[account_payment_sepa_credit_transfer](account_payment_sepa_credit_transfer/) | 18.0.3.0.0 |  | Create SEPA XML files for Credit Transfers
[account_payment_sepa_direct_debit](account_payment_sepa_direct_debit/) | 18.0.3.0.0 |  | Create SEPA files for Direct Debit

[//]: # (end addons)

<!-- prettier-ignore-end -->

## Licenses

This repository is licensed under [AGPL-3.0](LICENSE).

However, each module can have a totally different license, as long as they adhere to Odoo Community Association (OCA)
policy. Consult each module's `__manifest__.py` file, which contains a `license` key
that explains its license.

----
OCA, or the [Odoo Community Association](http://odoo-community.org/), is a nonprofit
organization whose mission is to support the collaborative development of Odoo features
and promote its widespread use.
