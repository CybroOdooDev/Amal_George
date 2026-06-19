# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from datetime import datetime, timedelta


class TestPosTopSellingProductsReport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestPosTopSellingProductsReport, cls).setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Top Product',
            'available_in_pos': True,
            'default_code': 'TPP01',
        })

        cls.pos_config = cls.env['pos.config'].create({'name': 'Test Config'})
        cls.pos_session = cls.env['pos.session'].create({
            'config_id': cls.pos_config.id,
            'user_id': cls.env.user.id,
        })
        cls.pos_session.action_pos_session_open()

        cls.pos_order = cls.env['pos.order'].create({
            'session_id': cls.pos_session.id,
            'amount_total': 300.0,
            'amount_tax': 0.0,
            'amount_paid': 300.0,
            'amount_return': 0.0,
            'state': 'paid',
            'lines': [(0, 0, {
                'product_id': cls.product.id,
                'qty': 6.0,
                'price_unit': 50.0,
                'price_subtotal': 300.0,
                'price_subtotal_incl': 300.0,
            })],
        })

        cls.report = cls.env['report.advanced_pos_reports.report_pos_top_selling_products']

    def test_get_top_selling_products_details(self):
        """ Test top selling products details aggregation and limit """
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now() + timedelta(days=1)

        # Test without limit
        res = self.report.get_top_selling_products_details(0, start_date, end_date)
        my_products = [p for p in res['products'] if (p['name'].get('en_US') if isinstance(p['name'], dict) else p['name']) == self.product.name]
        self.assertEqual(len(my_products), 1)
        self.assertEqual(my_products[0]['code'], 'TPP01')
        self.assertEqual(my_products[0]['qty'], 6.0)
        self.assertEqual(my_products[0]['total'], 300.0)

        # Test with limit
        res_limit = self.report.get_top_selling_products_details(1, start_date, end_date)
        self.assertTrue(len(res_limit['products']) >= 1)

    def test_get_report_values(self):
        """ Test _get_report_values updates report data correctly """
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now() + timedelta(days=1)
        data = {
            'no_of_products': 5,
            'start_date': start_date,
            'end_date': end_date,
        }
        res = self.report._get_report_values(docids=[], data=data)
        self.assertIn('products', res)
