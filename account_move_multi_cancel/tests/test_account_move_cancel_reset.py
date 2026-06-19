# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestAccountMoveCancelResetWizard(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_move_1 = cls.env['account.move'].create({
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
        cls.test_move_2 = cls.env['account.move'].create({
            'move_type': 'entry',
            'line_ids': [
                (0, None, {
                    'name': 'test line 3',
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'debit': 200.0,
                    'credit': 0.0,
                }),
                (0, None, {
                    'name': 'test line 4',
                    'account_id': cls.company_data['default_account_expense'].id,
                    'debit': 0.0,
                    'credit': 200.0,
                }),
            ]
        })

    def setUp(self):
        super().setUp()
        # Add the cancel/reset group to the active test user
        group_cancel = self.env.ref('account_move_multi_cancel.account_move_multi_cancel_group_user')
        self.env.user.write({'groups_id': [(4, group_cancel.id)]})

    def test_action_mass_journal_entry_cancel_success(self):
        """ Test mass cancel wizard action on posted moves """
        # Post the moves first
        self.test_move_1.action_post()
        self.test_move_2.action_post()
        self.assertEqual(self.test_move_1.state, 'posted')
        self.assertEqual(self.test_move_2.state, 'posted')

        # Create wizard with active_ids in context
        wizard = self.env['account.move.cancel.reset'].with_context(
            active_ids=[self.test_move_1.id, self.test_move_2.id]
        ).create({})

        wizard.action_mass_journal_entry_cancel()
        self.assertEqual(self.test_move_1.state, 'cancel')
        self.assertEqual(self.test_move_2.state, 'cancel')

    def test_action_mass_journal_entry_cancel_validation_error(self):
        """ Test mass cancel raises ValidationError if any move is not posted """
        # Keep moves in draft state
        self.assertEqual(self.test_move_1.state, 'draft')

        wizard = self.env['account.move.cancel.reset'].with_context(
            active_ids=[self.test_move_1.id, self.test_move_2.id]
        ).create({})

        with self.assertRaises(ValidationError):
            wizard.action_mass_journal_entry_cancel()

    def test_action_mass_journal_entry_reset_success(self):
        """ Test mass reset wizard action on canceled moves """
        # Post and then cancel the moves
        self.test_move_1.action_post()
        self.test_move_2.action_post()
        self.test_move_1.button_cancel()
        self.test_move_2.button_cancel()
        self.assertEqual(self.test_move_1.state, 'cancel')
        self.assertEqual(self.test_move_2.state, 'cancel')

        # Create wizard with active_ids in context
        wizard = self.env['account.move.cancel.reset'].with_context(
            active_ids=[self.test_move_1.id, self.test_move_2.id]
        ).create({})

        wizard.action_mass_journal_entry_reset()
        self.assertEqual(self.test_move_1.state, 'draft')
        self.assertEqual(self.test_move_2.state, 'draft')

    def test_action_mass_journal_entry_reset_validation_error(self):
        """ Test mass reset raises ValidationError if any move is not canceled """
        # Post the moves (not canceled)
        self.test_move_1.action_post()
        self.assertEqual(self.test_move_1.state, 'posted')

        wizard = self.env['account.move.cancel.reset'].with_context(
            active_ids=[self.test_move_1.id, self.test_move_2.id]
        ).create({})

        with self.assertRaises(ValidationError):
            wizard.action_mass_journal_entry_reset()
