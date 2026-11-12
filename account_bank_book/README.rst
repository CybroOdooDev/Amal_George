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

Bank Book Reports
================
Generate Bank Book Report in Both PDF and XLSX format

Key Features
------------
* **Comprehensive Bank Book Reporting**: Tracks all bank cash inflows, outflows, and running balances with complete transaction details including dates, partners, entry labels, and move references.
* **Dual Format Export (Excel & PDF)**: Export reports to formatted Microsoft Excel (.xlsx) spreadsheets or print-ready PDF documents with a single click.
* **Multi-Bank Journal Selection**: Filter and report on individual or multiple bank journals simultaneously for comprehensive reconciliation.
* **Custom Date Range Filtering**: Specify custom Start Date and End Date to analyze banking activities across any fiscal timeframe.
* **Target Move Flexibility**: Generate reports considering only posted entries or include draft entries for preliminary reviews.
* **Opening & Closing Balance Tracking**: Computes and displays initial balances, periodic debit/credit activity, and final closing balances for complete financial accuracy.
* **Display Account Filtering**: Filter to show all bank accounts or only those accounts with transaction movements within the selected period.


Installation
------------
* Ensure the required dependency **Base Accounting Kit** (``base_accounting_kit``) is installed or present in your addons path.
* Python package ``xlsxwriter`` is required for Excel report generation (included in standard Odoo environments).
* Place the ``account_bank_book`` module into your Odoo custom addons directory.
* Restart your Odoo server and update the addons list via **Apps -> Update Apps List** (in Developer Mode).
* Search for ``Bank Book Report`` (technical name: ``account_bank_book``) and click **Install**.

Configuration
-------------
No additional configuration is required.

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
