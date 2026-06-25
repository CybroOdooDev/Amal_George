# -*- coding: utf-8 -*-
import json
from odoo.tests import common, tagged

class DummyStream:
    def write(self, data):
        pass

class DummyResponse:
    def __init__(self):
        self.stream = DummyStream()

@tagged('post_install', '-at_install')
class TestInventoryReport(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env['dynamic.inventory.report'].create({
            'report_type': 'report_by_transfers',
        })

    def test_inventory_report_methods(self):
        """Test dynamic inventory report data generation methods"""
        option = [self.report.id]
        
        # Test get_filter_data
        filters = self.report.get_filter_data(option)
        self.assertEqual(filters['report_type'], 'report_by_transfers')

        # Test get_filter
        filters_label = self.report.get_filter(option)
        self.assertEqual(filters_label['report_type'], 'Report By Transfers')

        # Test inventory_report
        res = self.report.inventory_report(option)
        self.assertEqual(res['name'], "Inventory Orders")
        self.assertIn('report_lines', res)

        # Test get_xlsx_report for different report types
        response = DummyResponse()
        filter_str = json.dumps({'report_type': 'report_by_transfers'})
        # Outgoing transfers report
        data_transfers = json.dumps([
            {
                'name': 'WH/OUT/00001',
                'scheduled_date': '2026-06-25 12:00:00',
                'origin': 'SO001',
                'company': self.env.company.name,
                'partner': 'Test Partner',
                'state': 'done'
            }
        ])
        self.report.get_xlsx_report(filter_str, response, data_transfers)

        # Category report type
        self.report.report_type = 'report_by_categories'
        filter_str_cat = json.dumps({'report_type': 'report_by_categories'})
        data_cat = json.dumps([
            {
                'category': 'All',
                'name': {'en_US': 'Test Product'},
                'create_date': '2026-06-25 12:00:00',
                'value_float': 100.0,
                'quantity': 5.0
            }
        ])
        self.report.get_xlsx_report(filter_str_cat, response, data_cat)

        # Warehouse report type
        self.report.report_type = 'report_by_warehouse'
        filter_str_wh = json.dumps({'report_type': 'report_by_warehouse'})
        data_wh = json.dumps([
            {
                'name': 'San Francisco',
                'write_date': '2026-06-25 12:00:00',
                'company': self.env.company.name,
                'location': 'WH/Stock',
                'route': {'en_US': 'Receipt'}
            }
        ])
        self.report.get_xlsx_report(filter_str_wh, response, data_wh)

        # Location report type
        self.report.report_type = 'report_by_location'
        filter_str_loc = json.dumps({'report_type': 'report_by_location'})
        data_loc = json.dumps([
            {
                'complete_name': 'WH/Stock',
                'location_type': 'internal',
                'create_date': '2026-06-25 12:00:00',
                'company': self.env.company.name
            }
        ])
        self.report.get_xlsx_report(filter_str_loc, response, data_loc)
