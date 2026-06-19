# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestPosConfig(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestPosConfig, cls).setUpClass()
        # Find parent view location belonging to active company to prevent company mismatch
        parent_loc = cls.env['stock.location'].search([
            ('usage', '=', 'view'),
            ('company_id', '=', cls.env.company.id)
        ], limit=1)
        cls.location = cls.env['stock.location'].create({
            'name': 'Test Internal Location',
            'usage': 'internal',
            'location_id': parent_loc.id if parent_loc else False,
            'company_id': cls.env.company.id,
        })
        # Create products (type='consu' with is_storable=True represents storable products in Odoo 18)
        cls.product_pos = cls.env['product.product'].create({
            'name': 'POS Product',
            'available_in_pos': True,
            'type': 'consu',
            'is_storable': True,
        })
        cls.product_non_pos = cls.env['product.product'].create({
            'name': 'Non-POS Product',
            'available_in_pos': False,
            'type': 'consu',
            'is_storable': True,
        })
        # Setup stock quants
        cls.env['stock.quant'].create({
            'product_id': cls.product_pos.id,
            'location_id': cls.location.id,
            'quantity': 15.0,
        })
        cls.env['stock.quant'].create({
            'product_id': cls.product_non_pos.id,
            'location_id': cls.location.id,
            'quantity': 25.0,
        })
        # Create POS config
        cls.pos_config = cls.env['pos.config'].create({
            'name': 'Test POS Config',
        })

    def test_get_location_summary(self):
        """ Test that get_location_summary returns only active POS products with correct quantities """
        summary = self.pos_config.get_location_summary(self.location.id)
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]['product_id'], self.product_pos.id)
        self.assertEqual(summary[0]['product'], self.product_pos.name)
        self.assertEqual(summary[0]['quantity'], 15.0)

    def test_load_pos_data_models(self):
        """ Test that load_pos_data_models loads stock.location """
        pos_session = self.env['pos.session']
        models = pos_session._load_pos_data_models(self.pos_config.id)
        self.assertIn('stock.location', models)

    def test_load_pos_data(self):
        """ Test loading of stock.location data into POS """
        data = {
            'pos.config': {
                'data': [{'id': self.pos_config.id}]
            }
        }
        loaded = self.env['stock.location']._load_pos_data(data)
        self.assertIn('data', loaded)
        self.assertIn('fields', loaded)

        location_ids = [loc['id'] for loc in loaded['data']]
        self.assertIn(self.location.id, location_ids)
