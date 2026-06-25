# -*- coding: utf-8 -*-
from odoo.tests import common, tagged

@tagged('post_install', '-at_install')
class TestStockPickingReturnLine(common.TransactionCase):

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

    def test_stock_picking_return_line_computations(self):
        """Test catch weight logic on return picking line"""
        wizard = self.env['stock.return.picking'].with_context(active_id=self.picking.id).create({})
        return_line = self.env['stock.return.picking.line'].create({
            'wizard_id': wizard.id,
            'product_id': self.product.id,
            'quantity': 2.0,
            'move_id': self.move.id,
            'uom_id': self.uom_unit.id,
        })

        return_line._compute_cw_hide()
        self.assertTrue(return_line.cw_hide)

        return_line._compute_cw_uom_id()
        self.assertEqual(return_line.cw_uom_id, self.product.cw_uom_id)

        return_line._compute_cw_qty()
        self.assertEqual(return_line.cw_qty, 24.0)

        # Test onchange cw_qty
        return_line.cw_qty = 36.0
        return_line._onchange_cw_qty()
        self.assertEqual(return_line.quantity, 3.0)
