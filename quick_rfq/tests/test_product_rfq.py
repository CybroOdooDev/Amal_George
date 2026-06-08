# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestProductRfq(TransactionCase):
    """Test cases for the ProductRfq transient model in quick_rfq."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create vendor
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Test Vendor',
        })

        # Create product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'standard_price': 50.0,
            'type': 'consu',
        })

    def test_action_create_rfq_validation(self):
        """Test that validation fails (UserError) if no partner_id is selected."""
        wizard = self.env['product.rfq'].create({
            'rfq_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 5.0,
                'price_unit': 45.0,
            })]
        })

        with self.assertRaises(UserError, msg="Should raise UserError when partner_id is missing"):
            wizard.action_create_rfq()

        with self.assertRaises(UserError, msg="Should raise UserError when partner_id is missing"):
            wizard.action_create_view_rfq()

    def test_action_create_rfq_success(self):
        """Test that action_create_rfq creates a purchase order successfully."""
        wizard = self.env['product.rfq'].create({
            'partner_id': self.vendor.id,
            'rfq_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 5.0,
                'price_unit': 45.0,
            })]
        })

        # Count purchase orders before
        po_count_before = self.env['purchase.order'].search_count([('partner_id', '=', self.vendor.id)])

        wizard.action_create_rfq()

        # Count purchase orders after
        po_count_after = self.env['purchase.order'].search_count([('partner_id', '=', self.vendor.id)])
        self.assertEqual(po_count_after, po_count_before + 1, "A new purchase order should be created.")

        po = self.env['purchase.order'].search([('partner_id', '=', self.vendor.id)], order='id desc', limit=1)
        self.assertEqual(po.user_id, wizard.user_id)
        self.assertEqual(po.date_order, wizard.date_order)
        self.assertEqual(len(po.order_line), 1)
        self.assertEqual(po.order_line.product_id, self.product)
        self.assertEqual(po.order_line.product_qty, 5.0)
        self.assertEqual(po.order_line.price_unit, 45.0)

    def test_action_create_view_rfq_success(self):
        """Test that action_create_view_rfq creates a purchase order and returns form action."""
        wizard = self.env['product.rfq'].create({
            'partner_id': self.vendor.id,
            'rfq_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 2.0,
                'price_unit': 50.0,
            })]
        })

        action = wizard.action_create_view_rfq()

        # Check action properties
        self.assertEqual(action.get('type'), 'ir.actions.act_window')
        self.assertEqual(action.get('res_model'), 'purchase.order')
        self.assertEqual(action.get('view_mode'), 'form')
        self.assertEqual(action.get('target'), 'current')

        # Check PO
        po_id = action.get('res_id')
        self.assertTrue(po_id)
        po = self.env['purchase.order'].browse(po_id)
        self.assertTrue(po.exists())
        self.assertEqual(po.partner_id, self.vendor)
        self.assertEqual(po.order_line.product_id, self.product)
        self.assertEqual(po.order_line.product_qty, 2.0)
        self.assertEqual(po.order_line.price_unit, 50.0)
