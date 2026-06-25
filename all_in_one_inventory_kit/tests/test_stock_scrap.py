# -*- coding: utf-8 -*-
from odoo.tests import common, tagged

@tagged('post_install', '-at_install')
class TestStockScrap(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.brand = cls.env['product.brand'].create({'name': 'Test Brand'})
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen')
        
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product Scrap',
            'type': 'consu',
            'is_storable': True,
            'catch_weight_ok': True,
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'cw_uom_id': cls.uom_dozen.id,
            'average_cw_qty': 12.0,
        })
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TWH',
        })

    def test_stock_scrap_cw_computations(self):
        """Test computed catch weight fields on stock.scrap"""
        scrap = self.env['stock.scrap'].create({
            'product_id': self.product.id,
            'scrap_qty': 5.0,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.warehouse.lot_stock_id.id,
        })

        self.assertEqual(scrap.cw_uom_id, self.product.cw_uom_id)
        self.assertTrue(scrap.toggle_cw)
        
        scrap._compute_cw_qty()
        self.assertEqual(scrap.cw_qty, 60.0)
