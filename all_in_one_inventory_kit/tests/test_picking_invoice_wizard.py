# -*- coding: utf-8 -*-
from odoo.tests import common, tagged

@tagged('post_install', '-at_install')
class TestPickingInvoiceWizard(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.product = cls.env['product.product'].create({
            'name': 'Test Invoice Product',
            'type': 'consu',
            'is_storable': True,
            'lst_price': 50.0,
        })
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TWH',
        })
        
        # Create Sales Journal and Purchase Journal
        cls.sales_journal = cls.env['account.journal'].create({
            'name': 'Customer Invoice Journal',
            'code': 'CIV',
            'type': 'sale',
        })
        cls.purchase_journal = cls.env['account.journal'].create({
            'name': 'Vendor Bill Journal',
            'code': 'VBI',
            'type': 'purchase',
        })
        
        # Configure Config Parameters
        cls.env['ir.config_parameter'].sudo().set_param(
            'stock_move_invoice.customer_journal_id', cls.sales_journal.id)
        cls.env['ir.config_parameter'].sudo().set_param(
            'stock_move_invoice.vendor_journal_id', cls.purchase_journal.id)

    def test_picking_multi_invoice_action(self):
        """Test wizard action_picking_multi_invoice bulk creating invoice"""
        # Create outgoing picking
        picking_type_out = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', self.warehouse.id),
            ('code', '=', 'outgoing')
        ], limit=1)
        
        # Add stock so we can validate outgoing picking
        self.env['stock.quant'].create({
            'product_id': self.product.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'quantity': 10.0,
        })

        picking_out = self.env['stock.picking'].create({
            'picking_type_id': picking_type_out.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'partner_id': self.partner.id,
        })
        move = self.env['stock.move'].create({
            'name': 'Test Out Move',
            'product_id': self.product.id,
            'product_uom_qty': 5.0,
            'product_uom': self.product.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        picking_out.action_confirm()
        move.quantity = 5.0
        picking_out.button_validate()

        # Run multi invoice wizard with outgoing picking
        wizard = self.env['picking.invoice.wizard'].with_context(
            active_ids=[picking_out.id]
        ).create({})
        wizard.action_picking_multi_invoice()

        # Verify invoice created
        picking_out._compute_invoice_count()
        self.assertEqual(picking_out.invoice_count, 1)
        invoice = self.env['account.move'].search([('picking_id', '=', picking_out.id)], limit=1)
        self.assertEqual(invoice.move_type, 'out_invoice')
