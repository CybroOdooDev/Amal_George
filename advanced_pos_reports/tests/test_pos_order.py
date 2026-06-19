# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestPosOrder(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestPosOrder, cls).setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'POS Customer'})
        cls.category = cls.env['pos.category'].create({'name': 'Test POS Category'})

        cls.product = cls.env['product.product'].create({
            'name': 'POS Product with Category',
            'available_in_pos': True,
            'pos_categ_ids': [(6, 0, cls.category.ids)],
            'default_code': 'PPC01',
        })

        # Create POS config and session
        cls.pos_config = cls.env['pos.config'].create({'name': 'Test Config'})
        cls.pos_session = cls.env['pos.session'].create({
            'config_id': cls.pos_config.id,
            'user_id': cls.env.user.id,
        })
        cls.pos_session.action_pos_session_open()

        # Create POS order
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

    def test_get_category_summary(self):
        """ Test category summary returns correct category and amount """
        summary = self.env['pos.order'].get_category_summary([self.pos_order.id])
        self.assertEqual(len(summary), 1)
        categ_name = summary[0]['name']
        if isinstance(categ_name, dict):
            self.assertEqual(categ_name.get('en_US'), self.category.name)
        else:
            self.assertEqual(categ_name, self.category.name)
        self.assertEqual(summary[0]['id'], self.category.id)
        self.assertEqual(summary[0]['amount'], 100.0)
        self.assertEqual(summary[0]['qty'], 5.0)

    def test_get_product_summary(self):
        """ Test product summary returns correct product code and quantity """
        summary = self.env['pos.order'].get_product_summary([self.pos_order.id])
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]['id'], self.product.id)
        prod_name = summary[0]['name']
        if isinstance(prod_name, dict):
            self.assertEqual(prod_name.get('en_US'), self.product.name)
        else:
            self.assertEqual(prod_name, self.product.name)
        self.assertEqual(summary[0]['code'], 'PPC01')
        self.assertEqual(summary[0]['qty'], 5.0)

    def test_get_order_summary(self):
        """ Test order summary returns order metadata """
        summary = self.env['pos.order'].get_order_summary([self.pos_order.id])
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]['order_name'], self.pos_order.name)
        self.assertEqual(summary[0]['id'], self.pos_order.id)
        self.assertEqual(summary[0]['amount_total'], 100.0)
