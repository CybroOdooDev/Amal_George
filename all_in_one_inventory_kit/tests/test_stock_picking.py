# -*- coding: utf-8 -*-
from odoo.tests import common, tagged
from odoo.exceptions import UserError

@tagged('post_install', '-at_install')
class TestStockPicking(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.brand = cls.env['product.brand'].create({'name': 'Test Brand'})
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product Barcode',
            'type': 'consu',
            'is_storable': True,
            'barcode': '987654321',
            'lst_price': 100.0,
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

    def test_stock_picking_barcode(self):
        """Test scanning product barcode on stock.picking"""
        picking_type_out = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', self.warehouse.id),
            ('code', '=', 'outgoing')
        ], limit=1)
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type_out.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        # Scan incorrect barcode
        picking.barcode = '111111'
        res = picking._onchange_barcode()
        self.assertIn('warning', res)

        # Create move
        move = self.env['stock.move'].create({
            'name': 'Test Move Barcode',
            'product_id': self.product.id,
            'product_uom_qty': 1.0,
            'product_uom': self.product.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        
        # Scan correct barcode
        picking.barcode = '987654321'
        picking._onchange_barcode()
        self.assertEqual(move.product_uom_qty, 2.0)

        # Test writing with context barcode_processed
        picking.with_context(barcode_processed=True).write({'barcode': '987654321'})
        self.assertEqual(move.product_uom_qty, 3.0)

    def test_stock_picking_invoice_creation(self):
        """Test creating customer invoice, vendor bill, and refund credit notes"""
        picking_type_out = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', self.warehouse.id),
            ('code', '=', 'outgoing')
        ], limit=1)
        picking_out = self.env['stock.picking'].create({
            'picking_type_id': picking_type_out.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'partner_id': self.partner.id,
        })
        self.env['stock.move'].create({
            'name': 'Test Move Out',
            'product_id': self.product.id,
            'product_uom_qty': 5.0,
            'product_uom': self.product.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        picking_out.action_confirm()
        
        # Test action_create_invoice
        invoice = picking_out.action_create_invoice()
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.move_type, 'out_invoice')
        
        # Test action_create_vendor_credit
        vendor_credit = picking_out.action_create_vendor_credit()
        self.assertIsNotNone(vendor_credit)
        self.assertEqual(vendor_credit.move_type, 'in_refund')

        # Test compute_invoice_count
        picking_out._compute_invoice_count()
        self.assertEqual(picking_out.invoice_count, 2) # invoice + credit note

        # Test smart button action
        action = picking_out.action_open_picking_invoice()
        self.assertEqual(action['res_model'], 'account.move')

        # Test incoming picking actions
        picking_type_in = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', self.warehouse.id),
            ('code', '=', 'incoming')
        ], limit=1)
        picking_in = self.env['stock.picking'].create({
            'picking_type_id': picking_type_in.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
            'partner_id': self.partner.id,
        })
        self.env['stock.move'].create({
            'name': 'Test Move In',
            'product_id': self.product.id,
            'product_uom_qty': 5.0,
            'product_uom': self.product.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
        })
        picking_in.action_confirm()

        # Test action_create_bill
        bill = picking_in.action_create_bill()
        self.assertIsNotNone(bill)
        self.assertEqual(bill.move_type, 'in_invoice')

        # Test action_create_customer_credit
        customer_credit = picking_in.action_create_customer_credit()
        self.assertIsNotNone(customer_credit)
        self.assertEqual(customer_credit.move_type, 'out_refund')

    def test_stock_picking_rpc_methods(self):
        """Test RPC data retrieval methods used by dashboard tiles"""
        picking_type_out = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', self.warehouse.id),
            ('code', '=', 'outgoing')
        ], limit=1)
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type_out.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'partner_id': self.partner.id,
        })
        res_op = self.env['stock.picking'].get_operation_types()
        self.assertEqual(len(res_op), 5)
        
        res_cat = self.env['stock.picking'].get_product_category()
        self.assertIn('name', res_cat)
        self.assertIn('count', res_cat)

        res_loc = self.env['stock.picking'].get_locations()
        self.assertIsNotNone(res_loc)
