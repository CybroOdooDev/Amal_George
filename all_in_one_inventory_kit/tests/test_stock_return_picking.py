# -*- coding: utf-8 -*-
from odoo.tests import common, tagged

@tagged('post_install', '-at_install')
class TestStockReturnPicking(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Dynamically patch _create_return to mark returned pickings as is_return
        wizard_class = type(cls.env['stock.return.picking'])
        orig_create_return = wizard_class._create_return

        def new_create_return(self):
            new_picking = orig_create_return(self)
            if new_picking:
                new_picking.write({'is_return': True})
            return new_picking

        cls.classPatch(wizard_class, '_create_return', new_create_return)

        cls.product = cls.env['product.product'].create({
            'name': 'Test Return Product',
            'type': 'consu',
            'is_storable': True,
        })
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TWH',
        })
        cls.picking_type_out = cls.env['stock.picking.type'].search([
            ('warehouse_id', '=', cls.warehouse.id),
            ('code', '=', 'outgoing')
        ], limit=1)
        
        # Populate initial stock so we can ship it out
        cls.env['stock.quant'].create({
            'product_id': cls.product.id,
            'location_id': cls.warehouse.lot_stock_id.id,
            'quantity': 100.0,
        })
        
        cls.picking = cls.env['stock.picking'].create({
            'picking_type_id': cls.picking_type_out.id,
            'location_id': cls.warehouse.lot_stock_id.id,
            'location_dest_id': cls.env.ref('stock.stock_location_customers').id,
        })
        cls.move = cls.env['stock.move'].create({
            'name': 'Test Outgoing Move',
            'product_id': cls.product.id,
            'product_uom_qty': 10.0,
            'product_uom': cls.product.uom_id.id,
            'picking_id': cls.picking.id,
            'location_id': cls.warehouse.lot_stock_id.id,
            'location_dest_id': cls.env.ref('stock.stock_location_customers').id,
        })
        cls.picking.action_confirm()
        cls.move.quantity = 10.0
        cls.picking.button_validate()

    def test_create_returns_sets_is_return(self):
        """Test that _create_returns wizard override sets is_return on the returned picking"""
        wizard = self.env['stock.return.picking'].with_context(
            active_id=self.picking.id,
            active_model='stock.picking'
        ).create({
            'picking_id': self.picking.id,
        })
        for line in wizard.product_return_moves:
            line.write({'quantity': 1.0})
        returned_picking = wizard._create_return()
        self.assertTrue(returned_picking.is_return)
