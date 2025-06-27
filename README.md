
[![Runboat](https://img.shields.io/badge/runboat-Try%20me-875A7B.png)](https://runboat.odoo-community.org/builds?repo=OCA/bank-payment-alternative&target_branch=18.0)
[![Pre-commit Status](https://github.com/OCA/bank-payment-alternative/actions/workflows/pre-commit.yml/badge.svg?branch=18.0)](https://github.com/OCA/bank-payment-alternative/actions/workflows/pre-commit.yml?query=branch%3A18.0)
[![Build Status](https://github.com/OCA/bank-payment-alternative/actions/workflows/test.yml/badge.svg?branch=18.0)](https://github.com/OCA/bank-payment-alternative/actions/workflows/test.yml?query=branch%3A18.0)
[![codecov](https://codecov.io/gh/OCA/bank-payment-alternative/branch/18.0/graph/badge.svg)](https://codecov.io/gh/OCA/bank-payment-alternative)
[![Translation Status](https://translation.odoo-community.org/widgets/bank-payment-alternative-18-0/-/svg-badge.svg)](https://translation.odoo-community.org/engage/bank-payment-alternative-18-0/?utm_source=widget)

<!-- /!\ do not modify above this line -->

# Bank Payment - Alternative approach based on Odoo native payment methods

Alternative to https://github.com/OCA/bank-payment, based on Odoo native payment methods.

<!-- /!\ do not modify below this line -->

<!-- prettier-ignore-start -->

[//]: # (addons)

Available addons
----------------
addon | version | maintainers | summary
--- | --- | --- | ---
[account_payment_base_oca](account_payment_base_oca/) | 18.0.1.3.0 | <a href='https://github.com/alexis-via'><img src='https://github.com/alexis-via.png' width='32' height='32' style='border-radius:50%;' alt='alexis-via'/></a> | OCA extensions to native payment objects of Odoo
[account_payment_base_oca_sale](account_payment_base_oca_sale/) | 18.0.1.0.0 |  | Adds payment method on sale orders
[account_payment_batch_oca](account_payment_batch_oca/) | 18.0.1.1.0 |  | Add payment orders and debit orders
[account_payment_mandate](account_payment_mandate/) | 18.0.1.1.0 |  | Add support for banking mandates used in direct debits
[account_payment_mandate_sale](account_payment_mandate_sale/) | 18.0.1.0.0 | <a href='https://github.com/alexis-via'><img src='https://github.com/alexis-via.png' width='32' height='32' style='border-radius:50%;' alt='alexis-via'/></a> | Adds mandates on sale orders
[account_payment_sepa_base](account_payment_sepa_base/) | 18.0.1.0.0 |  | Base module for SEPA file generation
[account_payment_sepa_credit_transfer](account_payment_sepa_credit_transfer/) | 18.0.1.0.0 |  | Create SEPA XML files for Credit Transfers
[account_payment_sepa_direct_debit](account_payment_sepa_direct_debit/) | 18.0.1.0.0 |  | Create SEPA files for Direct Debit

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
