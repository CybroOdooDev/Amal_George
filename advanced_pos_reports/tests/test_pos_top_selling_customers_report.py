# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from datetime import datetime, timedelta


class TestPosTopSellingCustomersReport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestPosTopSellingCustomersReport, cls).setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Top Customer'})

        cls.pos_config = cls.env['pos.config'].create({'name': 'Test Config'})
        cls.pos_session = cls.env['pos.session'].create({
            'config_id': cls.pos_config.id,
            'user_id': cls.env.user.id,
        })
        cls.pos_session.action_pos_session_open()

        cls.pos_order = cls.env['pos.order'].create({
            'session_id': cls.pos_session.id,
            'partner_id': cls.partner.id,
            'amount_total': 250.0,
            'amount_tax': 0.0,
            'amount_paid': 250.0,
            'amount_return': 0.0,
            'state': 'paid',
        })

        cls.report = cls.env['report.advanced_pos_reports.report_pos_top_selling_customers']

    def test_get_top_selling_customers_details(self):
        """ Test top selling customers details aggregation and limit """
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now() + timedelta(days=1)

        # Test without limit
        res = self.report.get_top_selling_customers_details(0, start_date, end_date)
        my_customers = [c for c in res['customers'] if c['name'] == self.partner.name]
        self.assertEqual(len(my_customers), 1)
        self.assertEqual(my_customers[0]['amount'], 250.0)

        # Test with limit
        res_limit = self.report.get_top_selling_customers_details(1, start_date, end_date)
        self.assertTrue(len(res_limit['customers']) >= 1)

    def test_get_report_values(self):
        """ Test _get_report_values updates report data correctly """
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now() + timedelta(days=1)
        data = {
            'no_of_customers': 5,
            'start_date': start_date,
            'end_date': end_date,
        }
        res = self.report._get_report_values(docids=[], data=data)
        self.assertIn('customers', res)
