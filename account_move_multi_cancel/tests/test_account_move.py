# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountMoveMultiCancel(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a test move in draft state
        cls.test_move = cls.env['account.move'].create({
            'move_type': 'entry',
            'line_ids': [
                (0, None, {
                    'name': 'test line 1',
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'debit': 100.0,
                    'credit': 0.0,
                }),
                (0, None, {
                    'name': 'test line 2',
                    'account_id': cls.company_data['default_account_expense'].id,
                    'debit': 0.0,
                    'credit': 100.0,
                }),
            ]
        })

    def test_action_cancel_multiple_journal_entry(self):
        """ Test that action_cancel_multiple_journal_entry returns the correct wizard action """
        action = self.test_move.action_cancel_multiple_journal_entry()
        self.assertEqual(action.get('type'), 'ir.actions.act_window')
        self.assertEqual(action.get('res_model'), 'account.move.cancel.reset')
        self.assertEqual(action.get('target'), 'new')
        self.assertEqual(action.get('view_mode'), 'form')
        cancel_view = self.env.ref('account_move_multi_cancel.account_move_cancel_view_form')
        self.assertEqual(action.get('views')[0][0], cancel_view.id)

    def test_action_reset_multiple_journal_entry(self):
        """ Test that action_reset_multiple_journal_entry returns the correct wizard action """
        action = self.test_move.action_reset_multiple_journal_entry()
        self.assertEqual(action.get('type'), 'ir.actions.act_window')
        self.assertEqual(action.get('res_model'), 'account.move.cancel.reset')
        self.assertEqual(action.get('target'), 'new')
        self.assertEqual(action.get('view_mode'), 'form')
        reset_view = self.env.ref('account_move_multi_cancel.account_move_reset_view_form')
        self.assertEqual(action.get('views')[0][0], reset_view.id)
