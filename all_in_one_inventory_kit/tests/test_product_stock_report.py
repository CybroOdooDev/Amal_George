# -*- coding: utf-8 -*-
from odoo.tests import common, tagged

@tagged('post_install', '-at_install')
class TestProductStockReport(common.TransactionCase):

    def test_product_stock_report_values(self):
        """Test product stock report template _get_report_values"""
        product = self.env['product.product'].create({
            'name': 'Test Report Product',
        })
        
        report_model = self.env['report.all_in_one_inventory_kit.report_product_stock_template']
        res = report_model.with_context(active_ids=[product.id])._get_report_values([], {})
        self.assertIn(product, res['data'])
