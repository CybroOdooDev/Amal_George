# -*- coding: utf-8 -*-
import json
from odoo.tests.common import TransactionCase


class TestBaseRollback(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestBaseRollback, cls).setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})

    def test_write_creates_rollback_record(self):
        """ Test that writing to a standard model (e.g. res.partner) creates a rollback.record entry """
        rollback_count_before = self.env['rollback.record'].search_count([
            ('res_model', '=', 'res.partner'),
            ('record', '=', self.partner.id)
        ])

        self.partner.write({'name': 'Updated Test Partner', 'email': 'test@example.com'})

        rollback_records = self.env['rollback.record'].search([
            ('res_model', '=', 'res.partner'),
            ('record', '=', self.partner.id)
        ], order='id desc')

        self.assertEqual(len(rollback_records), rollback_count_before + 1)
        latest_rollback = rollback_records[0]

        # Verify the details of the rollback.record
        self.assertEqual(latest_rollback.res_model, 'res.partner')
        self.assertEqual(latest_rollback.record, self.partner.id)
        self.assertEqual(latest_rollback.user_id, self.env.user)

        # Verify history JSON contains written values
        history_vals = json.loads(latest_rollback.history)
        self.assertEqual(history_vals.get('name'), 'Updated Test Partner')
        self.assertEqual(history_vals.get('email'), 'test@example.com')

    def test_write_ir_module_module_no_rollback_record(self):
        """ Test that writing to ir.module.module does not create a rollback.record """
        module = self.env['ir.module.module'].search([('name', '=', 'base')], limit=1)
        self.assertTrue(module)

        rollback_count_before = self.env['rollback.record'].search_count([
            ('res_model', '=', 'ir.module.module')
        ])

        # Write to shortdesc (safe field)
        module.write({'shortdesc': 'Test Short Description'})

        rollback_count_after = self.env['rollback.record'].search_count([
            ('res_model', '=', 'ir.module.module')
        ])

        self.assertEqual(rollback_count_before, rollback_count_after)
