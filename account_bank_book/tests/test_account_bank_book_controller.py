# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(odoo@cybrosys.com)
#
#    This program is under the terms of the Odoo Proprietary License v1.0(OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the
#    Software or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NON INFRINGEMENT. IN NO EVENT SHALL
#    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,ARISING
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
###############################################################################
import json
from datetime import date
from odoo.tests import HttpCase, tagged, new_test_user


@tagged('post_install', '-at_install')
class TestAccountBankBookController(HttpCase):
    """Test suite for XLSXReportController (/bank_xlsx_reports)"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        cls.test_user = new_test_user(
            cls.env,
            login='bank_book_user',
            groups='base.group_user,account.group_account_user',
            company_id=cls.company.id,
        )

        # Ensure a bank journal and account exist
        cls.bank_journal = cls.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('company_id', '=', cls.company.id)
        ], limit=1)
        if not cls.bank_journal:
            cls.bank_journal = cls.env['account.journal'].create({
                'name': 'Controller Test Bank Journal',
                'type': 'bank',
                'code': 'CTBJ',
                'company_id': cls.company.id,
            })

        cls.bank_account = cls.bank_journal.default_account_id
        if not cls.bank_account:
            cls.bank_account = cls.env['account.account'].search([
                ('account_type', '=', 'asset_cash'),
                ('company_ids', 'in', cls.company.id)
            ], limit=1)
        if not cls.bank_account:
            cls.bank_account = cls.env['account.account'].create({
                'name': 'Controller Test Bank Account',
                'code': '101402',
                'account_type': 'asset_cash',
                'company_ids': [(6, 0, cls.company.ids)],
            })

        # Create and post a move for data
        cls.counterpart_account = cls.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_ids', 'in', cls.company.id)
        ], limit=1)
        if not cls.counterpart_account:
            cls.counterpart_account = cls.env['account.account'].create({
                'name': 'Controller Income Account',
                'code': '400102',
                'account_type': 'income',
                'company_ids': [(6, 0, cls.company.ids)],
            })

        cls.test_move = cls.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': cls.bank_journal.id,
            'date': date.today(),
            'line_ids': [
                (0, 0, {
                    'name': 'Controller Deposit',
                    'account_id': cls.bank_account.id,
                    'debit': 500.0,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': 'Controller Income',
                    'account_id': cls.counterpart_account.id,
                    'debit': 0.0,
                    'credit': 500.0,
                }),
            ]
        })
        cls.test_move.action_post()

    def test_01_bank_xlsx_reports_download(self):
        """Test sending valid POST request to /bank_xlsx_reports"""
        self.authenticate(self.test_user.login, 'bank_book_user')

        payload = {
            'output_format': 'xlsx',
            'report_name': 'Bank Book Report',
            'options': json.dumps({
                'form': {
                    'date_from': date.today().replace(day=1).isoformat(),
                    'date_to': date.today().isoformat(),
                    'journal_ids': self.bank_journal.ids,
                    'account_ids': self.bank_account.ids,
                    'target_move': 'posted',
                    'sortby': 'sort_date',
                    'display_account': 'all',
                    'initial_balance': True,
                    'used_context': {},
                }
            })
        }

        response = self.url_open('/bank_xlsx_reports', data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/vnd.ms-excel', response.headers.get('Content-Type', ''))
        self.assertIn('attachment', response.headers.get('Content-Disposition', ''))
        self.assertTrue(response.content.startswith(b'PK'))

    def test_02_bank_xlsx_reports_exception_handling(self):
        """Test exception serialization when invalid options are posted"""
        self.authenticate(self.test_user.login, 'bank_book_user')

        # Empty/invalid options to trigger exception block
        payload = {
            'output_format': 'xlsx',
            'report_name': 'Bank Book Report',
            'options': json.dumps({})
        }

        response = self.url_open('/bank_xlsx_reports', data=payload)
        self.assertEqual(response.status_code, 200)
        # Controller catches Exception and returns JSON with error data
        content = response.content.decode('utf-8', errors='ignore')
        self.assertIn('Odoo Server Error', content)

