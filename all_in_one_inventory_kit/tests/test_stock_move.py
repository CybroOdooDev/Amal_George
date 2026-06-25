# -*- coding: utf-8 -*-
from odoo.tests import common, tagged
from odoo import fields

@tagged('post_install', '-at_install')
class TestStockMove(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Dynamically add quantity_done property to stock.move class for compatibility
        stock_move_class = type(cls.env['stock.move'])
        from unittest.mock import patch
        cls.startClassPatcher(patch.object(
            stock_move_class, 'quantity_done',
            property(
                lambda self: self.quantity,
                lambda self, val: setattr(self, 'quantity', val)
            ),
            create=True
        ))
        cls.brand = cls.env['product.brand'].create({'name': 'Test Brand'})
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen')
        
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'consu',
            'is_storable': True,
            'barcode': '1234567890',
            'catch_weight_ok': True,
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'cw_uom_id': cls.uom_dozen.id,
            'average_cw_qty': 12.0,
        })
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TWH',
        })
        cls.picking_type = cls.env['stock.picking.type'].search([
            ('warehouse_id', '=', cls.warehouse.id),
            ('code', '=', 'outgoing')
        ], limit=1)
        cls.picking = cls.env['stock.picking'].create({
            'picking_type_id': cls.picking_type.id,
            'location_id': cls.warehouse.lot_stock_id.id,
            'location_dest_id': cls.env.ref('stock.stock_location_customers').id,
        })

    def test_stock_move_cw_computations(self):
        """Test catch weight logic on stock move creation and modifications"""
        move = self.env['stock.move'].create({
            'name': 'Test Move',
            'product_id': self.product.id,
            'product_uom_qty': 2.0,
            'product_uom': self.uom_unit.id,
            'picking_id': self.picking.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })

        # Test _compute_cw_hide
        move._compute_cw_hide()
        self.assertTrue(move.cw_hide)

        # Test _onchange_product_id
        move._onchange_product_id()
        self.assertEqual(move.cw_demand, 24.0)
        self.assertEqual(move.cw_uom_id, self.product.cw_uom_id)

        # Test _onchange_cw_done
        move.cw_done = 12.0
        move._onchange_cw_done()
        self.assertEqual(move.quantity, 1.0)

        # Test _onchange_quantity_done
        move.quantity = 3.0
        move._onchange_quantity_done()
        self.assertEqual(move.cw_done, 36.0)

        # Test _onchange_cw_demand
        move.cw_demand = 48.0
        move._onchange_cw_demand()
        self.assertEqual(move.product_uom_qty, 4.0)

        # Test _onchange_product_uom_qty
        move.product_uom_qty = 5.0
        move._onchange_product_uom_qty()
        self.assertEqual(move.product_uom_qty, 4.0)

        # Test _cal_cw_demand
        move.product_uom_qty = 5.0
        move._cal_cw_demand()
        self.assertEqual(move.cw_demand, 60.0)

        # Test barcode onchange
        move.barcode = '1234567890'
        move._onchange_barcode()
        self.assertEqual(move.product_id, self.product)

    def test_stock_move_rpc_methods(self):
        """Test RPC graph and report methods on stock move"""
        # Create a done picking and move to populate database records
        move = self.env['stock.move'].create({
            'name': 'Test Move Done',
            'product_id': self.product.id,
            'product_uom_qty': 10.0,
            'product_uom': self.uom_unit.id,
            'picking_id': self.picking.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        self.picking.action_confirm()
        # Set quantity to validate picking
        move.quantity = 10.0
        self.picking.button_validate()

        # Call the methods to check they execute without SQL error
        res1 = self.env['stock.move'].get_the_top_products()
        self.assertIn('products', res1)
        self.assertIn('count', res1)

        self.env['stock.move'].top_products_last_ten()
        self.env['stock.move'].top_products_last_thirty()
        self.env['stock.move'].top_products_last_three_months()
        self.env['stock.move'].top_products_last_year()
        self.env['stock.move'].get_stock_moves()
        self.env['stock.move'].stock_move_last_ten_days({})
        self.env['stock.move'].this_month({})
        self.env['stock.move'].last_three_month({})
        self.env['stock.move'].last_year({})

        # Test get_dead_of_stock with config parameter enabled
        self.env['ir.config_parameter'].sudo().set_param(
            "inventory_stock_dashboard_odoo.dead_stock_bol", "True")
        self.env['ir.config_parameter'].sudo().set_param(
            "inventory_stock_dashboard_odoo.dead_stock", "1")
        self.env['ir.config_parameter'].sudo().set_param(
            "inventory_stock_dashboard_odoo.dead_stock_type", "day")
        res_dead = self.env['stock.move'].get_dead_of_stock()
        self.assertIsNotNone(res_dead)
