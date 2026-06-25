# -*- coding: utf-8 -*-
from odoo.tests import common, tagged

@tagged('post_install', '-at_install')
class TestStockQuant(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.brand = cls.env['product.brand'].create({'name': 'Test Brand'})
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product Quant',
            'type': 'consu',
            'is_storable': True,
            'brand_id': cls.brand.id,
        })
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TWH',
        })
        cls.location = cls.warehouse.lot_stock_id

    def test_stock_quant_computations(self):
        """Test computed quantity fields on stock.quant"""
        quant = self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.location.id,
            'quantity': 10.0,
            'company_id': self.env.company.id,
        })

        quant._compute_location_qty()
        # Since it's a new storable product with no moves:
        # virtual_available = 10, incoming = 0, outgoing = 0
        self.assertEqual(quant.virtual_available, 10.0)
        self.assertEqual(quant.incoming_qty, 0.0)
        self.assertEqual(quant.outgoing_qty, 0.0)
        self.assertEqual(quant.brand_id, self.brand)

    def test_stock_quant_rpc_get_out_of_stock(self):
        """Test RPC method for out of stock products"""
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.location.id,
            'quantity': 2.0,
            'company_id': self.env.company.id,
        })

        # Set config parameters
        self.env['ir.config_parameter'].sudo().set_param(
            "inventory_stock_dashboard_odoo.out_of_stock", "True")
        self.env['ir.config_parameter'].sudo().set_param(
            "inventory_stock_dashboard_odoo.out_of_stock_quantity", "5")

        res = self.env['stock.quant'].get_out_of_stock()
        self.assertIn('product_name', res)
        self.assertIn('total_quantity', res)
        # Verify the product quantity is listed since 2 < 5
        self.assertIn(2.0, res['total_quantity'])
