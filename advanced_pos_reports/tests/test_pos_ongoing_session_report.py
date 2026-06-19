# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestPosOngoingSessionReport(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestPosOngoingSessionReport, cls).setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Customer'})
        cls.category = cls.env['pos.category'].create({'name': 'Test POS Category'})

        cls.product = cls.env['product.product'].create({
            'name': 'POS Product',
            'available_in_pos': True,
            'pos_categ_ids': [(6, 0, cls.category.ids)],
        })

        # Find or create receivable account using company_ids
        receivable_account = cls.env['account.account'].search([
            ('account_type', '=', 'asset_receivable'),
            ('company_ids', 'in', cls.env.company.id)
        ], limit=1)

        # Payment Method
        cls.payment_method = cls.env['pos.payment.method'].create({
            'name': 'Test Payment Method',
            'receivable_account_id': receivable_account.id if receivable_account else False,
        })

        cls.pos_config = cls.env['pos.config'].create({
            'name': 'Test Config',
            'payment_method_ids': [(6, 0, cls.payment_method.ids)],
        })
        cls.pos_session = cls.env['pos.session'].create({
            'config_id': cls.pos_config.id,
            'user_id': cls.env.user.id,
        })
        cls.pos_session.action_pos_session_open()
        # Force the state to 'opened' to match the query expectation
        cls.pos_session.state = 'opened'

        cls.pos_order = cls.env['pos.order'].create({
            'session_id': cls.pos_session.id,
            'partner_id': cls.partner.id,
            'amount_total': 100.0,
            'amount_tax': 0.0,
            'amount_paid': 100.0,
            'amount_return': 0.0,
            'state': 'paid',
            'lines': [(0, 0, {
                'product_id': cls.product.id,
                'qty': 5.0,
                'price_unit': 20.0,
                'price_subtotal': 100.0,
                'price_subtotal_incl': 100.0,
            })],
        })

        cls.pos_payment = cls.env['pos.payment'].create({
            'pos_order_id': cls.pos_order.id,
            'payment_method_id': cls.payment_method.id,
            'amount': 100.0,
        })

        cls.report = cls.env['report.advanced_pos_reports.report_pos_ongoing_session']

    def test_get_ongoing_sessions_details(self):
        """ Test ongoing session report details return expected aggregates """
        res = self.report.get_ongoing_sessions_details(self.pos_session.ids)
        self.assertIn('sessions', res)
        self.assertEqual(res['sessions'].ids, self.pos_session.ids)
        categ_name = res['categories'][0]['name']
        if isinstance(categ_name, dict):
            self.assertEqual(categ_name.get('en_US'), self.category.name)
        else:
            self.assertEqual(categ_name, self.category.name)
        self.assertEqual(res['categories'][0]['amount'], 100.0)
        # Handle payment method name translations
        pay_name = res['payments'][0]['name']
        if isinstance(pay_name, dict):
            self.assertEqual(pay_name.get('en_US'), self.payment_method.name)
        else:
            self.assertEqual(pay_name, self.payment_method.name)
        self.assertEqual(res['payments'][0]['total'], 100.0)

    def test_get_report_values(self):
        """ Test that _get_report_values updates report data correctly """
        data = {'session_ids': self.pos_session.ids}
        res = self.report._get_report_values(docids=[], data=data)
        self.assertIn('sessions', res)
        self.assertEqual(res['sessions'].ids, self.pos_session.ids)
