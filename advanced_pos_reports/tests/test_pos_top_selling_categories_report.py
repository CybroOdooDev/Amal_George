# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from datetime import datetime, timedelta


class TestPosTopSellingCategoriesReport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestPosTopSellingCategoriesReport, cls).setUpClass()
        cls.category = cls.env['pos.category'].create({'name': 'Top Category'})

        cls.product = cls.env['product.product'].create({
            'name': 'POS Product',
            'available_in_pos': True,
            'pos_categ_ids': [(6, 0, cls.category.ids)],
        })

        cls.pos_config = cls.env['pos.config'].create({'name': 'Test Config'})
        cls.pos_session = cls.env['pos.session'].create({
            'config_id': cls.pos_config.id,
            'user_id': cls.env.user.id,
        })
        cls.pos_session.action_pos_session_open()

        cls.pos_order = cls.env['pos.order'].create({
            'session_id': cls.pos_session.id,
            'amount_total': 150.0,
            'amount_tax': 0.0,
            'amount_paid': 150.0,
            'amount_return': 0.0,
            'state': 'paid',
            'lines': [(0, 0, {
                'product_id': cls.product.id,
                'qty': 3.0,
                'price_unit': 50.0,
                'price_subtotal': 150.0,
                'price_subtotal_incl': 150.0,
            })],
        })

        cls.report = cls.env['report.advanced_pos_reports.report_pos_top_selling_categories']

    def test_get_top_selling_categories_details(self):
        """ Test top selling categories details aggregation and limit """
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now() + timedelta(days=1)

        # Test without limit
        res = self.report.get_top_selling_categories_details(0, start_date, end_date)
        my_categs = [c for c in res['categories'] if (c['name'].get('en_US') if isinstance(c['name'], dict) else c['name']) == self.category.name]
        self.assertEqual(len(my_categs), 1)
        self.assertEqual(my_categs[0]['amount'], 150.0)

        # Test with limit
        res_limit = self.report.get_top_selling_categories_details(1, start_date, end_date)
        self.assertTrue(len(res_limit['categories']) >= 1)

    def test_get_report_values(self):
        """ Test _get_report_values updates report data correctly """
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now() + timedelta(days=1)
        data = {
            'no_of_categories': 5,
            'start_date': start_date,
            'end_date': end_date,
        }
        res = self.report._get_report_values(docids=[], data=data)
        self.assertIn('categories', res)
