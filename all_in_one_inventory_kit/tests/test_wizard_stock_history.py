# -*- coding: utf-8 -*-
import io
from odoo.tests import common, tagged

class DummyStream:
    def write(self, data):
        pass

class DummyResponse:
    def __init__(self):
        self.stream = DummyStream()

@tagged('post_install', '-at_install')
class TestWizardStockHistory(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env.ref('product.product_category_all')
        cls.product = cls.env['product.product'].create({
            'name': 'Test History Product',
            'type': 'consu',
            'categ_id': cls.category.id,
            'default_code': 'THP01',
            'standard_price': 15.0,
        })
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TWH',
        })
        # Set up a stock history wizard
        cls.wizard = cls.env['wizard.stock.history'].create({
            'warehouse_ids': [(4, cls.warehouse.id)],
            'category_ids': [(4, cls.category.id)],
        })

    def test_stock_history_wizard_methods(self):
        """Test wizard stock history methods and Excel generation"""
        # Test action_export_xlsx
        action = self.wizard.action_export_xlsx()
        self.assertEqual(action['type'], 'ir.actions.report')
        self.assertEqual(action['report_type'], 'stock_xlsx')

        # Test get_warehouse
        names, ids = self.wizard.get_warehouse(self.wizard)
        self.assertIn('Test Warehouse', names)
        self.assertIn(self.warehouse.id, ids)

        # Test get_lines
        lines = self.wizard.get_lines(self.category, self.warehouse.id)
        self.assertTrue(len(lines) > 0)
        line = [l for l in lines if l['sku'] == 'THP01'][0]
        self.assertEqual(line['name'], 'Test History Product')
        self.assertEqual(line['cost_price'], 15.0)

        # Test get_xlsx_report
        response = DummyResponse()
        data = {
            'ids': self.wizard.ids,
        }
        self.wizard.get_xlsx_report(data, response)
        # Should execute workbook writing and close stream without exception
