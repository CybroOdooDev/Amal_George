# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestPosPayment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestPosPayment, cls).setUpClass()
        # Find or create receivable account using company_ids Many2many relation
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

        cls.pos_order = cls.env['pos.order'].create({
            'session_id': cls.pos_session.id,
            'amount_total': 50.0,
            'amount_tax': 0.0,
            'amount_paid': 50.0,
            'amount_return': 0.0,
        })

        # Create payment
        cls.pos_payment = cls.env['pos.payment'].create({
            'pos_order_id': cls.pos_order.id,
            'payment_method_id': cls.payment_method.id,
            'amount': 50.0,
        })

    def test_get_payment_summary(self):
        """ Test that get_payment_summary aggregates payment details correctly by method """
        summary = self.env['pos.payment'].get_payment_summary([self.pos_payment.id])
        self.assertEqual(len(summary), 1)
        pay_name = summary[0]['name']
        if isinstance(pay_name, dict):
            self.assertEqual(pay_name.get('en_US'), self.payment_method.name)
        else:
            self.assertEqual(pay_name, self.payment_method.name)
        self.assertEqual(summary[0]['id'], self.payment_method.id)
        self.assertEqual(summary[0]['total'], 50.0)
