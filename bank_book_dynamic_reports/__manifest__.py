# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    This program is under the terms of the Odoo Proprietary License v1.0
#    (OPL-1) It is forbidden to publish, distribute, sublicense, or
#    sell copies of the Software or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
#    CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT
#    OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR
#    THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
###############################################################################
{
    'name': 'Dynamic Bank Book Reports', 
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'This module creates dynamic Bank Book reports.',
    'description': 'Generates dynamic bank book report.Bank book is a '
                   'subsidiary book which helps in checking the bank balances '
                   'at any point of time.',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'live_test_url': 'https://www.youtube.com/watch?v=P2LzTezdmkU',
    'depends': ['web', 'account', 'account_bank_book'],
    'data': [
        'wizard/account_bank_book_report_view.xml',
            ],
    'assets': {
        'web.assets_backend': [
            'bank_book_dynamic_reports/static/src/js/bank_book_dynamic.js',
            'bank_book_dynamic_reports/static/src/xml/ParentLine.xml',
            'bank_book_dynamic_reports/static/src/xml/report_template.xml'
        ],
    },
    'images': ['static/description/banner.jpg'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'price': 10,
    'currency': 'EUR',
    'application': False,
}
