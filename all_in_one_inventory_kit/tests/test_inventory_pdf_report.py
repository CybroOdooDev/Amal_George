# -*- coding: utf-8 -*-
from odoo.tests import common, tagged

@tagged('post_install', '-at_install')
class TestInventoryPdfReport(common.TransactionCase):

    def test_inventory_pdf_report_values(self):
        """Test fetching report values for inventory pdf report"""
        report_model = self.env['report.all_in_one_inventory_kit.inventory_pdf_report']
        data = {
            'report_data': {
                'report_lines': ['line1', 'line2'],
                'filters': {'report_type': 'report_by_transfers'},
            }
        }
        # Run with context
        res = report_model.with_context(inventory_pdf_report=True)._get_report_values([], data)
        self.assertIsNotNone(res)
        self.assertEqual(res['report_main_line_data'], ['line1', 'line2'])
        self.assertEqual(res['Filters'], {'report_type': 'report_by_transfers'})
        self.assertEqual(res['company'], self.env.company)
