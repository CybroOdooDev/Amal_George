# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class TestPosSaleTopSelling(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestPosSaleTopSelling, cls).setUpClass()
        # Set external report layout on company to avoid redirect to base.document.layout wizard
        layout = cls.env.ref('web.external_layout_standard', raise_if_not_found=False)
        if layout:
            cls.env.company.external_report_layout_id = layout.id

        cls.partner = cls.env['res.partner'].create({'name': 'Test Customer'})
        cls.pos_config = cls.env['pos.config'].create({'name': 'Test Config'})
        cls.pos_session = cls.env['pos.session'].create({
            'config_id': cls.pos_config.id,
            'user_id': cls.env.user.id,
        })
        cls.pos_session.action_pos_session_open()

        cls.product = cls.env['product.product'].create({
            'name': 'POS Product',
            'available_in_pos': True,
        })

        cls.pos_order = cls.env['pos.order'].create({
            'session_id': cls.pos_session.id,
            'partner_id': cls.partner.id,
            'amount_total': 100.0,
            'amount_tax': 0.0,
            'amount_paid': 100.0,
            'amount_return': 0.0,
            'lines': [(0, 0, {
                'product_id': cls.product.id,
                'qty': 5.0,
                'price_unit': 20.0,
                'price_subtotal': 100.0,
                'price_subtotal_incl': 100.0,
            })],
        })
        # Set state to paid so search query in wizard finds it
        cls.pos_order.state = 'paid'

    def test_validation_date_range(self):
        """ Test ValidationError is raised if start_date > end_date """
        wizard = self.env['pos.sale.top.selling'].create({
            'start_date': datetime.now() + timedelta(days=1),
            'end_date': datetime.now(),
            'top_selling': 'products',
        })
        with self.assertRaises(ValidationError):
            wizard.action_generate_report()

    def test_validation_no_orders(self):
        """ Test ValidationError is raised if no POS orders are found in range """
        wizard = self.env['pos.sale.top.selling'].create({
            'start_date': datetime.now() - timedelta(days=10),
            'end_date': datetime.now() - timedelta(days=9),
            'top_selling': 'products',
        })
        with self.assertRaises(ValidationError):
            wizard.action_generate_report()

    def test_generate_report_products(self):
        """ Test report generation for products """
        wizard = self.env['pos.sale.top.selling'].create({
            'start_date': datetime.now() - timedelta(days=1),
            'end_date': datetime.now() + timedelta(days=1),
            'top_selling': 'products',
            'no_of_products': 5,
        })
        action = wizard.action_generate_report()
        self.assertEqual(action.get('type'), 'ir.actions.report')
        self.assertEqual(action.get('report_name'), 'advanced_pos_reports.report_pos_top_selling_products')

    def test_generate_report_categories(self):
        """ Test report generation for categories """
        wizard = self.env['pos.sale.top.selling'].create({
            'start_date': datetime.now() - timedelta(days=1),
            'end_date': datetime.now() + timedelta(days=1),
            'top_selling': 'category',
            'no_of_categories': 5,
        })
        action = wizard.action_generate_report()
        self.assertEqual(action.get('type'), 'ir.actions.report')
        self.assertEqual(action.get('report_name'), 'advanced_pos_reports.report_pos_top_selling_categories')

    def test_generate_report_customers(self):
        """ Test report generation for customers """
        wizard = self.env['pos.sale.top.selling'].create({
            'start_date': datetime.now() - timedelta(days=1),
            'end_date': datetime.now() + timedelta(days=1),
            'top_selling': 'customers',
            'no_of_customers': 5,
        })
        action = wizard.action_generate_report()
        self.assertEqual(action.get('type'), 'ir.actions.report')
        self.assertEqual(action.get('report_name'), 'advanced_pos_reports.report_pos_top_selling_customers')
