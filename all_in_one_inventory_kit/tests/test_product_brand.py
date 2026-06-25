# -*- coding: utf-8 -*-
from odoo.tests import common, tagged

@tagged('post_install', '-at_install')
class TestProductBrand(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.brand = cls.env['product.brand'].create({
            'name': 'Test Brand',
        })
        cls.category = cls.env.ref('product.product_category_all')
        cls.product_tmpl = cls.env['product.template'].create({
            'name': 'Brand Product 1',
            'brand_id': cls.brand.id,
            'categ_id': cls.category.id,
        })

    def test_product_brand_computation(self):
        """Test brand fields and computed product count"""
        self.assertEqual(self.brand.name, 'Test Brand')
        self.assertEqual(int(self.brand.product_count), 1)
        
        # Add another product to the brand
        self.env['product.template'].create({
            'name': 'Brand Product 2',
            'brand_id': self.brand.id,
            'categ_id': self.category.id,
        })
        self.assertEqual(int(self.brand.product_count), 2)
