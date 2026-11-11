# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#############################################################################
{
    'name': 'Bank Book Report',
    'version': '20.0.1.0.0',
    'category': 'Accounting',
    'summary': "Generates bank book report in both PDF and XLSX formats.It is a"
               " subsidiary book which helps in checking the bank balances at "
               "any point of time. ",
    'description': "Generates bank book report in both PDF and XLSX formats,"
                   "Detailed bank book report,checking the bank balances,"
                   "Exporting the bank book report to Excel and PDF Format, "
                   "banking transactions,Accounting,Accounting XLSX Report,"
                   "Accounting PDF report, Report Exporting,Accounting module,"
                   "Odoo 18 Accounting.",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['base_accounting_kit', 'account'],
    'live_test_url': 'https://www.youtube.com/watch?v=yEdZtUDHxuM',
    'data': [
        'wizard/account_bank_book_report_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_bank_book/static/src/js/account_bank_book.js',
        ],
    },
    'images': ['static/description/banner.jpg'],
    'license': 'OPL-1',
    'price': 9.99,
    'currency': 'EUR',
    'installable': True,
    'auto_install': False,
    'application': False,
}
