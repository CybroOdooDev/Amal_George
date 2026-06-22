# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestProductBrand(TransactionCase):

    def test_product_brand_creation_and_count(self):
        """Test product brand creation and product templates count computation."""
        brand = self.env['product.brand'].create({
            'name': 'Test Brand',
        })
        # Trigger compute
        brand._compute_product_count()
        self.assertEqual(brand.product_count, '0')
        
        # Create product template with brand
        product_tmpl = self.env['product.template'].create({
            'name': 'Branded Product',
            'type': 'consu',
            'brand_id': brand.id,
        })
        
        brand._compute_product_count()
        self.assertEqual(brand.product_count, '1')
