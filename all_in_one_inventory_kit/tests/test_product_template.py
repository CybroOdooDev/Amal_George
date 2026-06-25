# -*- coding: utf-8 -*-
from odoo.tests import common, tagged

@tagged('post_install', '-at_install')
class TestProductTemplate(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.brand = cls.env['product.brand'].create({'name': 'Test Brand'})
        cls.categ_unit = cls.env.ref('uom.product_uom_categ_unit')
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen')
        
        cls.product_tmpl = cls.env['product.template'].create({
            'name': 'Test Template',
            'brand_id': cls.brand.id,
            'catch_weight_ok': True,
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
        })

    def test_onchange_cw_uom_id(self):
        """Test onchange method for calculating average_cw_qty"""
        self.product_tmpl.cw_uom_id = self.uom_dozen.id
        self.product_tmpl._onchange_cw_uom_id()
        # Since uom_unit and uom_dozen are in the same category (product_uom_categ_unit)
        # average_cw_qty should be self.cw_uom_id.factor / self.uom_id.factor
        # uom_unit factor is 1, dozen factor is 0.083333... wait, factor = 1 / ratio.
        # Let's verify standard UOM ratios: unit is 1.0, dozen is 0.08333333333333333.
        # So dozen factor is 0.08333333333333333, unit factor is 1.0.
        expected = self.uom_dozen.factor / self.uom_unit.factor
        self.assertAlmostEqual(self.product_tmpl.average_cw_qty, expected, places=4)

        # Set to different category
        categ_kgm = cls = self.env.ref('uom.product_uom_categ_kgm')
        uom_kg = self.env.ref('uom.product_uom_kgm')
        self.product_tmpl.cw_uom_id = uom_kg.id
        self.product_tmpl._onchange_cw_uom_id()
        self.assertEqual(self.product_tmpl.average_cw_qty, 1.00)
