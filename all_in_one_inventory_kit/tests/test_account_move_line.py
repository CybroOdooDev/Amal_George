# -*- coding: utf-8 -*-
from odoo.tests import common, tagged

@tagged('post_install', '-at_install')
class TestAccountMoveLine(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Invoice Partner',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Test Invoice Product',
            'type': 'consu',
            'is_storable': True,
            'lst_price': 100.0,
        })
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TWH',
        })
        cls.picking_type_out = cls.env['stock.picking.type'].search([
            ('warehouse_id', '=', cls.warehouse.id),
            ('code', '=', 'outgoing')
        ], limit=1)
        cls.picking_type_in = cls.env['stock.picking.type'].search([
            ('warehouse_id', '=', cls.warehouse.id),
            ('code', '=', 'incoming')
        ], limit=1)
        cls.picking = cls.env['stock.picking'].create({
            'picking_type_id': cls.picking_type_out.id,
            'location_id': cls.warehouse.lot_stock_id.id,
            'location_dest_id': cls.env.ref('stock.stock_location_customers').id,
        })
        
        # Setup Journal
        cls.journal = cls.env['account.journal'].create({
            'name': 'Test Invoice Journal',
            'code': 'TIJ',
            'type': 'sale',
        })

    def test_create_stock_moves_from_line(self):
        """Test _create_stock_moves helper method on account.move.line"""
        invoice = self.env['account.move'].with_context(default_move_type='out_invoice').create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
            'picking_type_id': self.picking_type_out.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 3.0,
                'price_unit': 120.0,
                'name': self.product.name,
            })]
        })
        
        line = invoice.invoice_line_ids[0]
        moves = line._create_stock_moves(self.picking)
        
        self.assertEqual(len(moves), 1)
        move = moves[0]
        self.assertEqual(move.product_id, self.product)
        self.assertEqual(move.product_uom_qty, 3.0)
        self.assertEqual(move.price_unit, 120.0)
        self.assertEqual(move.picking_id, self.picking)
