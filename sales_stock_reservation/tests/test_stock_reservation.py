# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#############################################################################
from odoo.tests import common
from odoo.tools.sql import column_exists


class TestStockReservation(common.TransactionCase):
    """Test cases for checking the product stock reservation lifecycle."""

    @classmethod
    def setUpClass(cls):
        super(TestStockReservation, cls).setUpClass()
        
        # Robust fix for inconsistent DB state:
        # Some modules (like website_sale) add REQUIRED and STORED fields to product.template and product.product.
        # If those modules are installed in the DB but NOT loaded during this test run
        # (because they aren't dependencies), Postgres will fail on NOT NULL constraints.
        # We dynamically drop these constraints for the duration of this transaction.
        problematic_fields = {
            'product_template': ['publish_date', 'base_unit_count'],
            'product_product': ['base_unit_count'],
        }
        for table, columns in problematic_fields.items():
            for column in columns:
                if column_exists(cls.env.cr, table, column):
                    cls.env.cr.execute(
                        f"ALTER TABLE {table} ALTER COLUMN {column} DROP NOT NULL"
                    )

        # Create partner and product for the sale order
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'email': 'customer@example.com',
        })
        
        # In Odoo 17+, storable products are 'consu' with 'is_storable=True'
        cls.product = cls.env['product.product'].create({
            'name': 'Test Reserved Product',
            'type': 'consu',
            'is_storable': True,
        })
        
        # Get the default warehouse and its stock location
        cls.warehouse = cls.env['stock.warehouse'].search([
            ('company_id', '=', cls.env.company.id)
        ], limit=1)
        
        # Ensure we have enough stock to reserve
        cls.env['stock.quant']._update_available_quantity(
            cls.product, cls.warehouse.lot_stock_id, 100
        )

    def test_01_reservation_lifecycle(self):
        """Test creating a reservation, verifying it, and then cancelling it."""
        # 1. Create Sale Order
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'warehouse_id': self.warehouse.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 10.0,
            })],
        })

        # 2. Simulate opening the wizard and confirming the reservation
        wizard_action = sale_order.action_create_stock_reservation()
        # Create the wizard with the context provided by the action
        wizard = self.env['sale.stock.reservation'].with_context(
            wizard_action['context']
        ).create({})
        
        wizard.action_reserve_stock()
        
        # 3. Verify that stock was reserved correctly
        self.assertEqual(sale_order.state_reservation, 'reserved',
                         "Sale Order reservation state should be 'reserved'.")
        self.assertTrue(sale_order.reserved_stock_ids,
                        "Reserved stock records should be created.")
        
        reserved_line = sale_order.reserved_stock_ids[0]
        self.assertEqual(reserved_line.reserved_quantity, 10.0,
                         "Reserved quantity should match the order line.")
        self.assertEqual(reserved_line.status, 'reserved',
                         "Status of reserved line should be 'reserved'.")
        
        # Check that the stock move was created and is active (confirmed or assigned)
        move = reserved_line.move_id
        self.assertTrue(move, "A stock move should be linked to the reservation.")
        self.assertIn(move.state, ['confirmed', 'assigned'],
                         "The stock move should be in 'confirmed' or 'assigned' state.")

        # Check that an email was sent to the customer
        customer_mail = self.env['mail.mail'].search([
            ('email_to', '=', self.partner.email),
        ])
        self.assertTrue(customer_mail, "An email should be sent to the customer upon stock reservation.")

        # Check that a reservation confirmation note is posted in the chatter
        chatter_msg = sale_order.message_ids.filtered(
            lambda m: "Stock Reservation Confirmed" in (m.body or '')
        )
        self.assertTrue(chatter_msg, "A confirmation note should be posted in the sale order chatter.")

        # 4. Manually cancel the reservation
        sale_order.action_cancel_reservation()
        
        # Verify that the reservation and moves are cancelled
        self.assertEqual(sale_order.state_reservation, 'cancel',
                         "Sale Order reservation state should be 'cancel'.")
        self.assertEqual(reserved_line.status, 'cancelled',
                         "Status of reserved line should be 'cancelled'.")
        self.assertEqual(move.state, 'cancel',
                         "The stock move should be in 'cancel' state.")

    def test_02_auto_cancel_on_confirm(self):
        """Test that confirming a Sale Order automatically cancels its reservation."""
        # Create and reserve stock for a Sale Order
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'warehouse_id': self.warehouse.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
            })],
        })
        
        wizard_action = sale_order.action_create_stock_reservation()
        wizard = self.env['sale.stock.reservation'].with_context(
            wizard_action['context']
        ).create({})
        wizard.action_reserve_stock()
        
        # Confirm the Sale Order
        sale_order.action_confirm()
        
        # Verify that the reservation is cancelled upon order confirmation
        self.assertEqual(sale_order.state_reservation, 'cancel',
                         "Reservation should be automatically cancelled on SO confirmation.")
        self.assertEqual(sale_order.reserved_stock_ids[0].status, 'cancelled',
                         "Reserved stock status should be 'cancelled'.")
        self.assertEqual(sale_order.reserved_stock_ids[0].move_id.state, 'cancel',
                         "Associated stock move should be cancelled.")
