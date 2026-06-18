# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestSaleOrderLineMultiWarehouse(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestSaleOrderLineMultiWarehouse, cls).setUpClass()
        cls.company = cls.env.company

        # Sanitize account_account table constraints for third-party modules (e.g. account_asset)
        cls.env.cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'account_account' AND column_name = 'create_asset'
        """)
        if cls.env.cr.fetchone():
            cls.env.cr.execute("ALTER TABLE account_account ALTER COLUMN create_asset DROP NOT NULL")

        # Setup Warehouses
        cls.warehouse_a = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)
        if not cls.warehouse_a:
            cls.warehouse_a = cls.env['stock.warehouse'].create({
                'name': 'Test Warehouse A',
                'code': 'TWA',
                'company_id': cls.company.id,
            })

        cls.warehouse_b = cls.env['stock.warehouse'].create({
            'name': 'Test Warehouse B',
            'code': 'TWB',
            'company_id': cls.company.id,
        })

        # Setup Partner/Customer
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
        })

        # Setup Product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Storable Product',
            'type': 'consu',
        })

    def test_multi_warehouse_pickings(self):
        """ Test that two different warehouses on sale order lines generate separate pickings """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'warehouse_id': self.warehouse_a.id,
        })

        self.env['sale.order.line'].create([
            {
                'order_id': sale_order.id,
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
                'product_warehouse_id': self.warehouse_a.id,
            },
            {
                'order_id': sale_order.id,
                'product_id': self.product.id,
                'product_uom_qty': 3.0,
                'product_warehouse_id': self.warehouse_b.id,
            }
        ])

        # Confirm the Sale Order
        sale_order.action_confirm()

        # Check pickings
        pickings = sale_order.picking_ids
        self.assertEqual(len(pickings), 2, "There should be exactly two stock pickings created.")

        picking_a = pickings.filtered(lambda p: p.picking_type_id.warehouse_id == self.warehouse_a)
        picking_b = pickings.filtered(lambda p: p.picking_type_id.warehouse_id == self.warehouse_b)

        self.assertTrue(picking_a, "A picking for Warehouse A should be created.")
        self.assertTrue(picking_b, "A picking for Warehouse B should be created.")

        self.assertEqual(sum(picking_a.move_ids.mapped('product_uom_qty')), 5.0, "Quantity for Warehouse A should be 5.0")
        self.assertEqual(sum(picking_b.move_ids.mapped('product_uom_qty')), 3.0, "Quantity for Warehouse B should be 3.0")

    def test_default_warehouse_picking(self):
        """ Test that when product_warehouse_id is not set, lines use the SO default warehouse """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'warehouse_id': self.warehouse_a.id,
        })

        self.env['sale.order.line'].create([
            {
                'order_id': sale_order.id,
                'product_id': self.product.id,
                'product_uom_qty': 4.0,
            },
            {
                'order_id': sale_order.id,
                'product_id': self.product.id,
                'product_uom_qty': 2.0,
            }
        ])

        # Confirm the Sale Order
        sale_order.action_confirm()

        # Check pickings
        pickings = sale_order.picking_ids
        self.assertEqual(len(pickings), 1, "There should be exactly one stock picking created.")
        self.assertEqual(pickings.picking_type_id.warehouse_id, self.warehouse_a, "The picking should belong to the default warehouse A.")
        self.assertEqual(sum(pickings.move_ids.mapped('product_uom_qty')), 6.0, "Total quantity on picking should be 6.0")
