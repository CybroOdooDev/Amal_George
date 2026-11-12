.. |license| image:: https://img.shields.io/badge/license-OPL--1-red.svg
    :target: http://www.gnu.org/licenses/opl-3.0-standalone.html
    :alt: License: OPL-1

.. |odoo| image:: https://img.shields.io/badge/Odoo-20.0-875A7B.svg
    :target: https://www.odoo.com
    :alt: Odoo 20.0

.. |maintainer| image:: https://img.shields.io/badge/maintainer-Cybrosys-875A7B.svg
    :target: https://cybrosys.com
    :alt: Maintainer: Cybrosys Techno Solutions

|license| |odoo| |maintainer|

Safer-pay Payment Gateway Integration
=====================================
Safer-pay is a modern, reliable, and secure payment service provider by Worldline. This module integrates the Saferpay Payment Gateway with your Odoo eCommerce website, enabling customers to securely process online payments via Saferpay's hosted payment interface.

Key Features
------------
* **Seamless eCommerce Checkout**: Direct integration with Odoo Website Sale, redirecting customers smoothly to the hosted Saferpay payment interface and returning them automatically to the order confirmation page.
* **PCI-DSS Level 1 Compliant Hosted Payment Page**: Cardholder data (credit/debit cards, CVVs) and 3-D Secure authentication are handled entirely on Worldline Saferpay's certified servers with zero sensitive card data stored on your Odoo instance.
* **Automated Payment & Order Confirmation**: Real-time transaction callback captures payment status, updates transaction records with provider reference tokens, and confirms sales orders automatically upon authorization.
* **Dual Sandbox & Production Environments**: Switch effortlessly between Saferpay Test Mode for safe simulation and Live Production mode using dedicated API credentials.
* **Multi-Currency & Global Payment Methods**: Process payments across global currencies (CHF, EUR, USD, GBP, etc.) supporting major card networks including Visa, Mastercard, American Express, and Diners Club.
* **Robust Error & Cancellation Handling**: Customers who abort or fail authorization are safely redirected back to the checkout page with their shopping cart intact and informative status notifications.
* **Odoo 20 Certified**: Built specifically for Odoo 20, compatible with both Community and Enterprise editions with full adherence to Odoo payment provider standards.

Installation
------------
* Requires the Python ``requests`` library.
* Install the module directly from the Odoo Apps dashboard or by placing the ``safer_pay`` directory in your custom addons path.

Configuration
-------------
1. Navigate to **Website > Configuration > Payment Providers** or **Invoicing > Configuration > Payment Providers**.
2. Select **Saferpay** and set the State to **Test Mode** or **Enabled**.
3. In the **Credentials** tab, provide your Saferpay account details:
   * **Customer ID**
   * **Terminal ID**
   * **JSON API Username**
   * **JSON API Password**
4. Publish the payment provider on your website to allow customers to pay via Saferpay.

Company
-------
* `Cybrosys Techno Solutions <https://cybrosys.com/>`__

License
-------
Odoo Proprietary License v1.0.
(http://www.gnu.org/licenses/opl-3.0-standalone.html)

Contacts
--------
* Mail Contact : odoo@cybrosys.com
* Website : https://cybrosys.com

Maintainer
==========
.. image:: https://cybrosys.com/images/logo.png
   :target: https://cybrosys.com


This module is maintained by Cybrosys Technologies.

For support and more information, please visit `Our Website <https://cybrosys.com/>`__
