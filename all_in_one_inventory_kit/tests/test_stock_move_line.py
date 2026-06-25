# -*- coding: utf-8 -*-
from odoo.tests import common, tagged

@tagged('post_install', '-at_install')
class TestStockMoveLine(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.brand = cls.env['product.brand'].create({'name': 'Test Brand'})
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen')
        
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'consu',
            'is_storable': True,
            'catch_weight_ok': True,
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'cw_uom_id': cls.uom_dozen.id,
            'average_cw_qty': 12.0,
            'brand_id': cls.brand.id,
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
        cls.move = cls.env['stock.move'].create({
            'name': 'Test Move',
            'product_id': cls.product.id,
            'product_uom_qty': 5.0,
            'product_uom': cls.uom_unit.id,
            'picking_id': cls.picking.id,
            'location_id': cls.warehouse.lot_stock_id.id,
            'location_dest_id': cls.env.ref('stock.stock_location_customers').id,
        })
        cls.picking.action_confirm()

    def test_stock_move_line_computations(self):
        """Test catch weight calculations and related fields on stock.move.line"""
        move_line = self.env['stock.move.line'].create({
            'move_id': self.move.id,
            'product_id': self.product.id,
            'product_uom_id': self.uom_unit.id,
            'quantity': 2.0,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'picking_id': self.picking.id,
        })

        move_line._compute_cw_hide()
        self.assertTrue(move_line.cw_hide)

        move_line._compute_cw_uom_id()
        self.assertEqual(move_line.cw_uom_id, self.product.cw_uom_id)

        move_line._compute_cw_qty_done()
        self.assertEqual(move_line.cw_qty_done, 24.0)

    def test_stock_move_line_rpc_methods(self):
        """Test RPC graph methods on stock.move.line"""
        move_line = self.env['stock.move.line'].create({
            'move_id': self.move.id,
            'product_id': self.product.id,
            'product_uom_id': self.uom_unit.id,
            'quantity': 5.0,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'picking_id': self.picking.id,
        })
        # Set picking to done
        self.move.quantity = 5.0
        self.picking.button_validate()

        res1, res2 = self.env['stock.move.line'].get_product_moves()
        self.assertIn('name', res1)
        self.assertIn('count', res1)
        self.assertIn('category_id', res2)

        res3 = self.env['stock.move.line'].product_move_by_category(self.product.categ_id.id)
        self.assertIn('name', res3)
        self.assertIn('count', res3)
