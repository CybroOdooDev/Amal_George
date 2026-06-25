# -*- coding: utf-8 -*-
from odoo.tests import common, tagged

@tagged('post_install', '-at_install')
class TestStockValuationLayer(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen')
        
        cls.product = cls.env['product.product'].create({
            'name': 'Test Valuation Product',
            'type': 'consu',
            'is_storable': True,
            'catch_weight_ok': True,
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'cw_uom_id': cls.uom_dozen.id,
            'average_cw_qty': 12.0,
        })

    def test_stock_valuation_layer_computations(self):
        """Test computed catch weight fields on stock.valuation.layer"""
        svl = self.env['stock.valuation.layer'].create({
            'product_id': self.product.id,
            'quantity': 3.0,
            'value': 300.0,
            'company_id': self.env.company.id,
        })

        svl._compute_cw_hide()
        self.assertTrue(svl.cw_hide)

        svl._compute_cw_uom_id()
        self.assertEqual(svl.cw_uom_id, self.product.cw_uom_id)

        svl._compute_cw_qty_done()
        self.assertEqual(svl.cw_qty_done, 36.0)
