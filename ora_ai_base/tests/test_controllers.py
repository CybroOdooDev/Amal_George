# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#############################################################################
import json
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.ora_ai_base.controllers.ora_ai_base import VapiAssistant, JsonResponse


@tagged('post_install', '-at_install')
class TestOraControllers(TransactionCase):
    """Unit tests for voice assistant webhook controller methods and data processing."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.controller = VapiAssistant()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Alice Wonder',
            'email': 'alice@example.com',
            'phone': '+1234567890',
        })

    def test_01_json_response_wrapper(self):
        """Test JsonResponse structure and content serialization."""
        data = {'status': 'success', 'code': 200}
        resp = JsonResponse(data, status=200)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['status'], 'success')
        self.assertEqual(resp.get('status'), 'success')
        self.assertIn('status', resp)

    def test_02_make_tool_response(self):
        """Test tool response formatting conforming to Vapi spec."""
        resp = self.controller._make_tool_response(
            tool_call_id='call_tool_xyz',
            result_str='Order SO001 successfully placed'
        )
        parsed = json.loads(resp.data.decode('utf-8'))
        self.assertIn('results', parsed)
        self.assertEqual(parsed['results'][0]['toolCallId'], 'call_tool_xyz')
        self.assertEqual(parsed['results'][0]['result'], 'Order SO001 successfully placed')

    def test_03_extract_tool_call(self):
        """Test extraction of toolCallId and arguments from nested webhook data."""
        data_nested = {
            'message': {
                'toolCalls': [{
                    'id': 'call_123',
                    'function': {
                        'arguments': {'customer_name': 'Alice Wonder'}
                    }
                }]
            }
        }
        tool_id, args = self.controller._extract_tool_call(data_nested)
        self.assertEqual(tool_id, 'call_123')
        self.assertEqual(args.get('customer_name'), 'Alice Wonder')

    def test_04_find_customer_by_name(self):
        """Test flexible customer name resolution in company context."""
        found = self.controller._find_customer_by_name('Alice Wonder', env=self.env)
        self.assertEqual(found, self.partner)

        found_partial = self.controller._find_customer_by_name('Alice Cooper', env=self.env)
        self.assertEqual(found_partial, self.partner)

        empty = self.controller._find_customer_by_name('', env=self.env)
        self.assertFalse(empty)
