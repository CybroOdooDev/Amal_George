# -*- coding: utf-8 -*-
import json
from odoo.tests.common import TransactionCase


class TestRollbackRecord(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestRollbackRecord, cls).setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Original Name',
            'email': 'original@example.com'
        })
        cls.partner_model = cls.env['ir.model'].search([('model', '=', 'res.partner')], limit=1)

    def test_action_record_selection(self):
        """ Test that executing action_record_selection on a rollback record restores the original record to the values in history """
        # Perform two edits
        self.partner.write({'name': 'First Edit', 'email': 'first@example.com'})

        # Get the rollback record generated from this write
        rollback_1 = self.env['rollback.record'].search([
            ('res_model', '=', 'res.partner'),
            ('record', '=', self.partner.id)
        ], order='id desc', limit=1)
        self.assertTrue(rollback_1)

        self.partner.write({'name': 'Second Edit', 'email': 'second@example.com'})

        self.assertEqual(self.partner.name, 'Second Edit')
        self.assertEqual(self.partner.email, 'second@example.com')

        # Revert back to rollback_1 (First Edit)
        action = rollback_1.action_record_selection()

        # Check action return values
        self.assertEqual(action.get('type'), 'ir.actions.client')
        self.assertEqual(action.get('tag'), 'reload')

        # Verify partner fields were updated
        self.assertEqual(self.partner.name, 'First Edit')
        self.assertEqual(self.partner.email, 'first@example.com')

    def test_get_models(self):
        """ Test that get_models returns the names of the models configured for rollback """
        # Configure partner model for rollback
        config = self.env['res.config.settings'].create({
            'res_rollback_model_ids': [(6, 0, self.partner_model.ids)]
        })
        config.set_values()

        # Fetch configured models
        configured_models = self.env['rollback.record'].get_models()
        self.assertIn('res.partner', configured_models)
