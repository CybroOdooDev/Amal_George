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
import io
from datetime import date
from odoo.tests import common, tagged
from odoo.exceptions import UserError


class MockResponse:
    """Mock HTTP Response object providing stream.write interface for xlsxwriter"""
    def __init__(self):
        self.stream = io.BytesIO()


@tagged('post_install', 'at_install')
class TestAccountBankBookReport(common.TransactionCase):
    """Test suite for Report Model (report.base_accounting_kit.report_bank_book)"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        cls.bank_journal = cls.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('company_id', '=', cls.company.id)
        ], limit=1)
        if not cls.bank_journal:
            cls.bank_journal = cls.env['account.journal'].create({
                'name': 'Test Bank Journal Report',
                'type': 'bank',
                'code': 'TBANKR',
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
                'name': 'Test Bank Account Report',
                'code': '101401',
                'account_type': 'asset_cash',
                'company_ids': [(6, 0, cls.company.ids)],
            })

        cls.counterpart_account = cls.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_ids', 'in', cls.company.id)
        ], limit=1)
        if not cls.counterpart_account:
            cls.counterpart_account = cls.env['account.account'].create({
                'name': 'Test Income Account Report',
                'code': '400101',
                'account_type': 'income',
                'company_ids': [(6, 0, cls.company.ids)],
            })

        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Report Partner',
        })

        # Post sample moves
        cls.move_1 = cls.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': cls.bank_journal.id,
            'date': date.today(),
            'line_ids': [
                (0, 0, {
                    'name': 'Customer Deposit',
                    'partner_id': cls.partner.id,
                    'account_id': cls.bank_account.id,
                    'debit': 2000.0,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': 'Revenue Balance',
                    'partner_id': cls.partner.id,
                    'account_id': cls.counterpart_account.id,
                    'debit': 0.0,
                    'credit': 2000.0,
                }),
            ]
        })
        cls.move_1.action_post()

        cls.report_model = cls.env['report.base_accounting_kit.report_bank_book']

    def test_01_get_account_move_entry_structure(self):
        """Test calculation of move entries and data structure"""
        accounts = self.bank_account
        res = self.report_model._get_account_move_entry(
            accounts=accounts,
            init_balance=True,
            sortby='sort_date',
            display_account='all'
        )
        self.assertIsInstance(res, list)
        if res:
            account_data = res[0]
            self.assertIn('code', account_data)
            self.assertIn('name', account_data)
            self.assertIn('debit', account_data)
            self.assertIn('credit', account_data)
            self.assertIn('balance', account_data)
            self.assertIn('move_lines', account_data)
            self.assertGreaterEqual(account_data['debit'], 2000.0)

    def test_02_get_account_move_entry_sorting(self):
        """Test sort options (date vs journal/partner)"""
        res_date = self.report_model._get_account_move_entry(
            accounts=self.bank_account,
            init_balance=False,
            sortby='sort_date',
            display_account='all'
        )
        res_journal = self.report_model._get_account_move_entry(
            accounts=self.bank_account,
            init_balance=False,
            sortby='sort_journal_partner',
            display_account='all'
        )
        self.assertIsInstance(res_date, list)
        self.assertIsInstance(res_journal, list)

    def test_03_get_xlsx_report_generation(self):
        """Test xlsx report writer successfully streams workbook content"""
        options = {
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
        }
        mock_response = MockResponse()
        self.report_model.get_xlsx_report(options, mock_response)
        output_data = mock_response.stream.getvalue()
        self.assertGreater(len(output_data), 0)
        # Check standard zip/xlsx magic bytes (PK..)
        self.assertTrue(output_data.startswith(b'PK'))

    def test_04_get_xlsx_report_missing_form_raises_user_error(self):
        """Test UserError when form dictionary is missing in options"""
        options = {'form': {}}
        mock_response = MockResponse()
        with self.assertRaises(UserError):
            self.report_model.get_xlsx_report(options, mock_response)

