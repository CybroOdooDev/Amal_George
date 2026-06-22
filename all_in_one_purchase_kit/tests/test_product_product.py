# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestProductProduct(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Vendor Product Test'})
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product Product',
            'type': 'consu',
        })
        cls.po = cls.env['purchase.order'].create({
            'partner_id': cls.partner.id,
        })

    def test_most_purchased_product(self):
        """Test most_purchased_product returns products list."""
        res = self.env['product.product'].most_purchased_product()
        self.assertIn('purchased_qty', res)

    def test_add_to_rfq(self):
        """Test adding product to RFQ via context order_id."""
        self.assertEqual(len(self.po.order_line), 0)
        
        # Call add_to_rfq with context
        product_ctx = self.product.with_context(order_id=self.po.id)
        product_ctx.add_to_rfq()
        
        self.assertEqual(len(self.po.order_line), 1)
        self.assertEqual(self.po.order_line.product_id, self.product)
