# -*- coding: utf-8 -*-
from odoo.tests import common, tagged
from odoo.exceptions import UserError

@tagged('post_install', '-at_install')
class TestAccountMove(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Invoice Partner',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Test Invoice Product',
            'type': 'consu',
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
        
        # Setup Journal
        cls.journal = cls.env['account.journal'].create({
            'name': 'Test Invoice Journal',
            'code': 'TIJ',
            'type': 'sale',
        })

    def test_account_move_stock_actions(self):
        """Test creating invoice and generating stock picking/moves from it"""
        invoice = self.env['account.move'].with_context(default_move_type='out_invoice').create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
            'picking_type_id': self.picking_type_out.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 2.0,
                'price_unit': 100.0,
                'name': self.product.name,
            })]
        })

        # Test _get_stock_type_ids
        type_res = invoice.with_context(default_move_type='out_invoice')._get_stock_type_ids()
        self.assertEqual(type_res.code, 'outgoing')

        # Test action_stock_move
        invoice.action_stock_move()
        self.assertTrue(invoice.invoice_picking_id)
        self.assertEqual(invoice.picking_count, 1)
        
        picking = invoice.invoice_picking_id
        self.assertEqual(picking.origin, invoice.name)
        self.assertEqual(len(picking.move_ids), 1)
        self.assertEqual(picking.move_ids.product_uom_qty, 2.0)

        # Test action_view_picking
        action = invoice.action_view_picking()
        self.assertEqual(action['res_model'], 'stock.picking')
        self.assertEqual(action['res_id'], picking.id)

        # Test _reverse_moves
        invoice.action_post()
        # Create reverse/credit note
        reverse_wz = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice.ids).create({
            'reason': 'test',
            'journal_id': self.journal.id,
        })
        res_reverse = reverse_wz.reverse_moves()
        reverse_move = self.env['account.move'].browse(res_reverse['res_id'])
        # The reverse move should have picking_type_id switched to incoming
        self.assertEqual(reverse_move.picking_type_id.code, 'incoming')
