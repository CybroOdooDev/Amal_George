# -*- coding: utf-8 -*-
from odoo.tests import common, tagged

@tagged('post_install', '-at_install')
class TestProductProduct(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'consu',
            'is_storable': True,
        })
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TWH',
        })
        cls.location = cls.warehouse.lot_stock_id
        # Create quant for this product and location
        cls.quant = cls.env['stock.quant'].create({
            'product_id': cls.product.id,
            'location_id': cls.location.id,
            'quantity': 10.0,
        })

    def test_product_fields_and_methods(self):
        """Test product_stock_location_ids and action_get_wo_description"""
        self.assertIn(self.quant, self.product.product_stock_location_ids)
        
        action = self.product.action_get_wo_description()
        self.assertIn(action.get('type'), ['ir.actions.report', 'ir.actions.act_window'])
