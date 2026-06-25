# -*- coding: utf-8 -*-
import json
from odoo.tests import HttpCase, tagged

@tagged('post_install', '-at_install')
class TestAllInOneReportExcel(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Set up some dummy data so the queries in controllers do not fail
        cls.brand = cls.env['product.brand'].create({'name': 'Test Brand'})
        cls.product = cls.env['product.product'].create({
            'name': 'Test Route Product',
            'type': 'consu',
            'is_storable': True,
            'barcode': '987654321',
        })
        cls.test_user = cls.env['res.users'].create({
            'name': 'Test Route User',
            'login': 'test_route_user',
            'password': 'testpassword',
            'groups_id': [(4, cls.env.ref('stock.group_stock_user').id)],
        })

    def test_json_routes(self):
        """Test public/user JSON RPC routes in the controller"""
        self.authenticate('test_route_user', 'testpassword')
        # Test get_operation_types
        response = self.url_open(
            '/get_operation_types',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'params': {}})
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertNotIn('error', res_data)

        # Test get_the_top_products
        response = self.url_open(
            '/get_the_top_products',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'params': {}})
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertNotIn('error', res_data)

        # Test get_stock_moves
        response = self.url_open(
            '/get_stock_moves',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'params': {}})
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertNotIn('error', res_data)

        # Test get_product_moves
        response = self.url_open(
            '/get_product_moves',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'params': {}})
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertNotIn('error', res_data)

        # Test get_product_category
        response = self.url_open(
            '/get_product_category',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'params': {}})
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertNotIn('error', res_data)

        # Test product_move_by_category
        response = self.url_open(
            '/product_move_by_category',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'params': {'args': self.product.categ_id.id}})
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertNotIn('error', res_data)

        # Test get_locations
        response = self.url_open(
            '/get_locations',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'params': {}})
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertNotIn('error', res_data)

        # Test get_out_of_stock
        response = self.url_open(
            '/get_out_of_stock',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'params': {}})
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertNotIn('error', res_data)

        # Test get_dead_of_stock
        response = self.url_open(
            '/get_dead_of_stock',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'params': {}})
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertNotIn('error', res_data)
