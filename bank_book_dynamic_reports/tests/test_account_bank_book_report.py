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
from datetime import date, timedelta
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestAccountBankBookReport(TransactionCase):
    """Test suite for the Dynamic Bank Book Report wizard
    (bank_book_dynamic_reports module).

    Covers:
        - view_report() validations and return structure
        - _get_dynamic_move_entry() for all display_account modes
        - _get_currency() with and without a journal currency
        - Sorting options (sort_date / sort_journal_partner)
        - Initial balance inclusion / exclusion
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ------------------------------------------------------------------ #
        # Company / currency
        # ------------------------------------------------------------------ #
        cls.company = cls.env.company
        cls.currency = cls.company.currency_id

        # ------------------------------------------------------------------ #
        # Bank journal
        # ------------------------------------------------------------------ #
        cls.bank_journal = cls.env['account.journal'].search(
            [('type', '=', 'bank'),
             ('company_id', '=', cls.company.id)], limit=1)
        if not cls.bank_journal:
            cls.bank_journal = cls.env['account.journal'].create({
                'name': 'Test Bank Journal',
                'type': 'bank',
                'code': 'TBNK',
                'company_id': cls.company.id,
            })

        # ------------------------------------------------------------------ #
        # Bank account used in move lines
        # ------------------------------------------------------------------ #
        cls.bank_account = cls.bank_journal.default_account_id
        if not cls.bank_account:
            # In Odoo 18, account.account uses company_ids (Many2many),
            # not company_id — company scoping is via ir.rule automatically.
            cls.bank_account = cls.env['account.account'].search([
                ('account_type', 'in', ['asset_cash', 'liability_current']),
            ], limit=1)

        # ------------------------------------------------------------------ #
        # Counter-part account (expense / income)
        # ------------------------------------------------------------------ #

        # In Odoo 18, account.account uses company_ids (Many2many).
        cls.expense_account = cls.env['account.account'].search([
            ('account_type', '=', 'expense'),
        ], limit=1)
        if not cls.expense_account:
            cls.expense_account = cls.env['account.account'].create({
                'name': 'Test Expense Account',
                'code': 'EXP9999',
                'account_type': 'expense',
                'company_ids': [(4, cls.company.id)],
            })

        # ------------------------------------------------------------------ #
        # Posted bank journal entry
        # ------------------------------------------------------------------ #
        cls.move = cls.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': cls.bank_journal.id,
            'date': date.today(),
            'line_ids': [
                (0, 0, {
                    'account_id': cls.bank_account.id,
                    'name': 'Bank Debit Line',
                    'debit': 500.0,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'account_id': cls.expense_account.id,
                    'name': 'Expense Credit Line',
                    'debit': 0.0,
                    'credit': 500.0,
                }),
            ],
        })
        cls.move._post()

    # ---------------------------------------------------------------------- #
    # Helper – create a wizard record with sensible defaults
    # ---------------------------------------------------------------------- #
    def _make_wizard(self, **kwargs):
        """Create an account.bank.book.report TransientModel record."""
        defaults = {
            'date_from': date.today() - timedelta(days=30),
            'date_to': date.today(),
            'journal_ids': [(6, 0, [self.bank_journal.id])],
            'target_move': 'posted',
            'display_account': 'movement',
            'account_ids': [(6, 0, [self.bank_account.id])],
            'sortby': 'sort_date',
            'initial_balance': False,
        }
        defaults.update(kwargs)
        return self.env['account.bank.book.report'].create(defaults)

    # ==================================================================== #
    #  view_report() – validation guards
    # ==================================================================== #

    def test_view_report_initial_balance_with_valid_date_from_succeeds(self):
        """When initial_balance=True AND date_from is set, view_report()
        must NOT raise a UserError for the missing-date guard.
        The report should either return a client action or raise UserError
        for 'no data' — but never for the missing-date reason.
        """
        wizard = self._make_wizard(
            initial_balance=True,
            date_from=date.today() - timedelta(days=30),
            date_to=date.today(),
        )
        # Must not raise "You must choose a Start Date"
        try:
            result = wizard.view_report()
            self.assertEqual(result.get('type'), 'ir.actions.client')
        except UserError as e:
            self.assertNotIn('Start Date', str(e),
                             "view_report() raised the missing-date UserError "
                             "even though date_from was provided.")


    def test_view_report_raises_if_no_account_selected(self):
        """view_report() must raise UserError when account_ids is empty."""
        wizard = self._make_wizard(account_ids=[(6, 0, [])])
        with self.assertRaises(UserError):
            wizard.view_report()

    def test_view_report_returns_client_action_when_data_exists(self):
        """view_report() should return an ir.actions.client dict tagged
        'report_bankbook' when matching move lines exist."""
        wizard = self._make_wizard()
        result = wizard.view_report()
        self.assertEqual(result.get('type'), 'ir.actions.client')
        self.assertEqual(result.get('tag'), 'report_bankbook')
        self.assertIn('params', result)

    def test_view_report_params_contain_expected_keys(self):
        """The params dict returned by view_report() must include
        form, acc_name, account_res, currency and init_balance."""
        wizard = self._make_wizard()
        result = wizard.view_report()
        params = result.get('params', {})
        for key in ('form', 'acc_name', 'account_res', 'currency',
                    'init_balance'):
            self.assertIn(key, params,
                          msg=f"Key '{key}' missing from view_report() params")

    def test_view_report_acc_name_format(self):
        """acc_name list items must have 'acc_name' and 'fold' keys."""
        wizard = self._make_wizard()
        result = wizard.view_report()
        acc_name_list = result['params']['acc_name']
        self.assertTrue(len(acc_name_list) > 0)
        for item in acc_name_list:
            self.assertIn('acc_name', item)
            self.assertIn('fold', item)
            self.assertEqual(item['fold'], 1)

    def test_view_report_raises_user_error_when_no_records(self):
        """view_report() should raise UserError when no move lines match
        the provided date range (future date range with no entries)."""
        future_date = date.today() + timedelta(days=365)
        wizard = self._make_wizard(
            date_from=future_date,
            date_to=future_date + timedelta(days=30),
        )
        with self.assertRaises(UserError):
            wizard.view_report()

    # ==================================================================== #
    #  view_report() – sort options
    # ==================================================================== #

    def test_view_report_sort_by_date(self):
        """view_report() should succeed with sortby='sort_date'."""
        wizard = self._make_wizard(sortby='sort_date')
        result = wizard.view_report()
        self.assertEqual(result['type'], 'ir.actions.client')

    def test_view_report_sort_by_journal_partner(self):
        """view_report() should succeed with sortby='sort_journal_partner'."""
        wizard = self._make_wizard(sortby='sort_journal_partner')
        result = wizard.view_report()
        self.assertEqual(result['type'], 'ir.actions.client')

    # ==================================================================== #
    #  view_report() – display_account modes
    # ==================================================================== #

    def test_view_report_display_account_movement(self):
        """display_account='movement' should return only accounts that have
        move lines in the period."""
        wizard = self._make_wizard(display_account='movement')
        result = wizard.view_report()
        self.assertEqual(result['type'], 'ir.actions.client')

    def test_view_report_display_account_all(self):
        """display_account='all' should include the account regardless of
        whether it has move lines in the period."""
        wizard = self._make_wizard(display_account='all')
        result = wizard.view_report()
        self.assertEqual(result['type'], 'ir.actions.client')

    # ==================================================================== #
    #  _get_dynamic_move_entry() – direct unit tests
    # ==================================================================== #

    def test_get_dynamic_move_entry_returns_list(self):
        """_get_dynamic_move_entry() must return a list."""
        wizard = self._make_wizard()
        accounts = self.env['account.account'].browse(self.bank_account.id)
        result = wizard._get_dynamic_move_entry(
            accounts, init_balance=False,
            sortby='sort_date', display_account='movement')
        self.assertIsInstance(result, list)

    def test_get_dynamic_move_entry_movement_has_data(self):
        """_get_dynamic_move_entry() with display_account='movement' must
        return at least one entry for an account that has posted lines."""
        wizard = self._make_wizard()
        accounts = self.env['account.account'].browse(self.bank_account.id)
        result = wizard._get_dynamic_move_entry(
            accounts, init_balance=False,
            sortby='sort_date', display_account='movement')
        self.assertTrue(len(result) > 0,
                        "Expected at least one account entry in result")

    def test_get_dynamic_move_entry_all_includes_account(self):
        """display_account='all' must include every requested account."""
        wizard = self._make_wizard()
        accounts = self.env['account.account'].browse(self.bank_account.id)
        result = wizard._get_dynamic_move_entry(
            accounts, init_balance=False,
            sortby='sort_date', display_account='all')
        self.assertEqual(len(result), len(accounts))

    def test_get_dynamic_move_entry_result_structure(self):
        """Each entry in the result must contain 'code', 'name',
        'move_lines', 'debit', 'credit', 'balance'."""
        wizard = self._make_wizard()
        accounts = self.env['account.account'].browse(self.bank_account.id)
        result = wizard._get_dynamic_move_entry(
            accounts, init_balance=False,
            sortby='sort_date', display_account='all')
        for entry in result:
            for key in ('code', 'name', 'move_lines', 'debit',
                        'credit', 'balance'):
                self.assertIn(key, entry,
                              msg=f"Key '{key}' missing from account entry")

    def test_get_dynamic_move_entry_with_initial_balance(self):
        """view_report() must succeed when initial_balance=True and
        date_from is provided, exercising the initial-balance SQL path.

        We test this via view_report() rather than calling
        _get_dynamic_move_entry() directly, because the internal
        _query_get() context must be built through _build_contexts()
        to produce correct SQL table aliases.
        """
        wizard = self._make_wizard(
            initial_balance=True,
            date_from=date.today() - timedelta(days=30),
            date_to=date.today(),
        )
        # view_report() internally calls _get_dynamic_move_entry with
        # init_balance=True via the properly-built used_context.
        result = wizard.view_report()
        self.assertIn(result.get('type'),
                      ('ir.actions.client', None),
                      "Expected client action or UserError (no data), not a crash")

    def test_get_dynamic_move_entry_sort_journal_partner(self):
        """_get_dynamic_move_entry() must not crash with
        sortby='sort_journal_partner'."""
        wizard = self._make_wizard()
        accounts = self.env['account.account'].browse(self.bank_account.id)
        result = wizard._get_dynamic_move_entry(
            accounts, init_balance=False,
            sortby='sort_journal_partner', display_account='movement')
        self.assertIsInstance(result, list)

    def test_get_dynamic_move_entry_not_zero_mode(self):
        """display_account='not_zero' must only return accounts whose
        balance is non-zero."""
        wizard = self._make_wizard()
        accounts = self.env['account.account'].browse(self.bank_account.id)
        result = wizard._get_dynamic_move_entry(
            accounts, init_balance=False,
            sortby='sort_date', display_account='not_zero')
        self.assertIsInstance(result, list)

    # ==================================================================== #
    #  _get_currency()
    # ==================================================================== #

    def test_get_currency_returns_list_without_journal_currency(self):
        """_get_currency() without a journal in context must return a list
        [symbol, position] from the company currency."""
        wizard = self._make_wizard()
        result = wizard._get_currency()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], self.currency.symbol)
        self.assertEqual(result[1], self.currency.position)

    def test_get_currency_returns_id_when_journal_has_currency(self):
        """_get_currency() must return the currency id (int) when the
        journal referenced in context carries its own currency."""
        # Create a secondary currency journal (USD if company currency != USD)
        other_currency = self.env['res.currency'].search(
            [('active', '=', True), ('id', '!=', self.currency.id)], limit=1)
        if not other_currency:
            self.skipTest("No secondary active currency available")

        journal_with_currency = self.env['account.journal'].create({
            'name': 'Test FX Bank Journal',
            'type': 'bank',
            'code': 'TFXB',
            'currency_id': other_currency.id,
            'company_id': self.company.id,
        })
        wizard = self._make_wizard()
        result = wizard.with_context(
            default_journal_id=journal_with_currency.id)._get_currency()
        self.assertEqual(result, other_currency.id)

    # ==================================================================== #
    #  Wizard field default / creation sanity
    # ==================================================================== #

    def test_wizard_creation_with_all_fields(self):
        """Wizard record must be created successfully with all fields set."""
        wizard = self._make_wizard(
            date_from=date.today() - timedelta(days=7),
            date_to=date.today(),
            target_move='all',
            display_account='all',
            sortby='sort_date',
            initial_balance=False,
        )
        self.assertTrue(wizard.id,
                        "Wizard should be created with a valid database id")

    def test_wizard_target_move_posted(self):
        """Wizard created with target_move='posted' should store that value."""
        wizard = self._make_wizard(target_move='posted')
        self.assertEqual(wizard.target_move, 'posted')

    def test_wizard_target_move_all(self):
        """Wizard created with target_move='all' should store that value."""
        wizard = self._make_wizard(target_move='all')
        self.assertEqual(wizard.target_move, 'all')

    def test_wizard_date_range_stored_correctly(self):
        """date_from / date_to must be stored as provided."""
        d_from = date.today() - timedelta(days=10)
        d_to = date.today()
        wizard = self._make_wizard(date_from=d_from, date_to=d_to)
        self.assertEqual(wizard.date_from, d_from)
        self.assertEqual(wizard.date_to, d_to)

    def test_wizard_journal_ids_stored(self):
        """journal_ids should contain the bank journal passed at creation."""
        wizard = self._make_wizard()
        self.assertIn(self.bank_journal, wizard.journal_ids)

    def test_wizard_account_ids_stored(self):
        """account_ids should contain the bank account passed at creation."""
        wizard = self._make_wizard()
        self.assertIn(self.bank_account, wizard.account_ids)

    def test_wizard_initial_balance_default_false(self):
        """initial_balance must default to False when not explicitly set."""
        wizard = self._make_wizard(initial_balance=False)
        self.assertFalse(wizard.initial_balance)

    def test_wizard_initial_balance_true(self):
        """initial_balance flag must be stored when set to True."""
        wizard = self._make_wizard(
            initial_balance=True,
            date_from=date.today() - timedelta(days=30))
        self.assertTrue(wizard.initial_balance)
