# -*- coding: utf-8 -*-
from ast import literal_eval
from odoo.tests.common import TransactionCase


class TestResConfigSettingsRollback(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestResConfigSettingsRollback, cls).setUpClass()
        cls.partner_model = cls.env['ir.model'].search([('model', '=', 'res.partner')], limit=1)
        cls.user_model = cls.env['ir.model'].search([('model', '=', 'res.users')], limit=1)

    def test_config_settings_set_and_get_values(self):
        """ Test setting and getting the res_rollback_model_ids in configuration settings """
        models_to_configure = self.partner_model | self.user_model

        # Create config settings instance
        config = self.env['res.config.settings'].create({
            'res_rollback_model_ids': [(6, 0, models_to_configure.ids)]
        })

        # Test set_values
        config.set_values()

        # Verify stored parameter
        stored_param = self.env['ir.config_parameter'].sudo().get_param(
            'odoo_record_rollback.res_rollback_model_ids'
        )
        self.assertTrue(stored_param)
        self.assertEqual(literal_eval(stored_param), models_to_configure.ids)

        # Test get_values
        retrieved_values = self.env['res.config.settings'].get_values()
        self.assertIn('res_rollback_model_ids', retrieved_values)
        self.assertEqual(retrieved_values['res_rollback_model_ids'], [(6, 0, models_to_configure.ids)])

    def test_config_settings_empty_values(self):
        """ Test configuration behavior when no models are selected """
        # Force set config parameter to False
        self.env['ir.config_parameter'].sudo().set_param(
            'odoo_record_rollback.res_rollback_model_ids', False
        )

        retrieved_values = self.env['res.config.settings'].get_values()
        self.assertIn('res_rollback_model_ids', retrieved_values)
        self.assertFalse(retrieved_values['res_rollback_model_ids'])
