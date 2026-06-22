# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestResPartner(TransactionCase):

    def test_res_partner_discount_and_po_stats(self):
        """Test default discount and purchase orders stats on partner."""
        partner = self.env['res.partner'].create({
            'name': 'Test Vendor Partner',
            'default_discount': 25.0,
        })
        self.assertEqual(partner.default_discount, 25.0)
            
        # Create some purchase orders for the partner to test get_vendor_po
        product = self.env['product.product'].create({
            'name': 'Partner PO Product',
            'type': 'consu',
        })
        po1 = self.env['purchase.order'].create({
            'partner_id': partner.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })]
        })
        po1.button_confirm()
        if po1.state != 'purchase':
            po1.write({'state': 'purchase'})
        
        # Flush to DB to compute purchase_order_count
        self.env.flush_all()
            
        stats = partner.get_vendor_po()
        self.assertIn('purchase_order_count', stats)
        self.assertEqual(stats['purchase_order_count'].get(partner.name), 1)
