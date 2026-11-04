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
import base64
from unittest.mock import patch
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install', 'ora_ai_base')
class TestOraAiBase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Voice Customer',
            'phone': '+15551234567',
            'email': 'voice_customer@test.com',
        })
        cls.category = cls.env['product.public.category'].create({
            'name': 'Beverages',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Iced Latte',
            'list_price': 5.50,
            'sale_ok': True,
            'public_categ_ids': [(6, 0, [cls.category.id])],
        })
        cls.provider_model = cls.env['provider.model'].search([], limit=1)
        if not cls.provider_model:
            cls.provider_model = cls.env['provider.model'].create({
                'name': 'GPT-4o',
                'key': 'gpt-4o',
                'provider': 'openai',
            })
        cls.transcriber_model = cls.env['transcriber.model'].search([], limit=1)
        if not cls.transcriber_model:
            cls.transcriber_model = cls.env['transcriber.model'].create({
                'name': 'Nova-2',
                'key': 'nova-2',
                'provider': 'deepgram',
            })
        cls.language = cls.env['ora.language'].search([], limit=1)
        if not cls.language:
            cls.language = cls.env['ora.language'].create({
                'name': 'English',
                'code': 'en',
                'voice': 'voice_123',
            })

        cls.assistant = cls.env['ora.ai'].create({
            'name': 'Test Store Assistant',
            'company_id': cls.company.id,
            'provider': 'openai',
            'provider_model_id': cls.provider_model.id,
            'transcriber_provider': 'deepgram',
            'transcriber_model_id': cls.transcriber_model.id,
            'language_id': cls.language.id,
        })

    def test_01_config_settings_and_parameters(self):
        """Test configuration parameters storage and retrieval."""
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_str('ora_ai_base.vapi_private_api_key', 'test_priv_key_123')
        ICP.set_str('ora_ai_base.vapi_public_api_key', 'test_pub_key_456')
        ICP.set_str('ora_ai_base.voice_order_auto_confirm', 'True')
        ICP.set_str('ora_ai_base.vapi_webhook_secret', 'secret_token_789')

        self.assertEqual(ICP.get_str('ora_ai_base.vapi_private_api_key'), 'test_priv_key_123')
        self.assertEqual(ICP.get_str('ora_ai_base.vapi_public_api_key'), 'test_pub_key_456')
        self.assertEqual(ICP.get_str('ora_ai_base.voice_order_auto_confirm'), 'True')
        self.assertEqual(ICP.get_str('ora_ai_base.vapi_webhook_secret'), 'secret_token_789')

    def test_02_prompt_generation_and_currency(self):
        """Test prompt computation includes company name, currency symbol, and product prices."""
        self.assistant._compute_prompt()
        prompt = self.assistant.prompt
        self.assertIn(self.company.name, prompt)
        self.assertIn(self.company.currency_id.symbol, prompt)
        self.assertIn('Iced Latte', prompt)
        self.assertIn(f"{self.product.list_price:.2f}", prompt)

    def test_03_bounded_function_description(self):
        """Test product mapping function description generation."""
        self.assistant._compute_function_description()
        desc = self.assistant.function_description
        self.assertIn(self.product.name, desc)
        self.assertIn(str(self.product.id), desc)

    def test_04_ora_file_mime_and_size_validation(self):
        """Test file creation, mime detection, and 25MB validation."""
        valid_pdf_data = base64.b64encode(b"%PDF-1.4 test file content").decode('utf-8')
        with patch('requests.post') as mock_post:
            mock_post.return_value.ok = True
            mock_post.return_value.json.return_value = {'id': 'vapi_file_001'}
            file_rec = self.env['ora.file'].create({
                'name': 'menu.pdf',
                'file': valid_pdf_data,
            })
            self.assertEqual(file_rec.name, 'menu.pdf')
            self.assertEqual(file_rec.state, 'uploaded')
            self.assertEqual(file_rec.id_file, 'vapi_file_001')

        # Test size limit exceeding 25MB
        huge_data = base64.b64encode(b"0" * (26 * 1024 * 1024)).decode('utf-8')
        with self.assertRaises(ValidationError):
            self.env['ora.file'].create({
                'name': 'large.pdf',
                'file': huge_data,
            })

    def test_05_call_history_logging(self):
        """Test call history logging, status progression, and idempotency."""
        status_payload = {
            'call_id': 'call_abc_123',
            'message': {
                'type': 'status-update',
                'call': {
                    'id': 'call_abc_123',
                    'type': 'webCall',
                    'assistantId': self.assistant.id_assistant or 'dummy_asst_id',
                    'startedAt': '2026-11-04T10:00:00Z',
                    'endedAt': '2026-11-04T10:02:30Z',
                    'cost': 0.125,
                },
                'transcript': 'Customer: Hello\nAssistant: Welcome!',
            }
        }
        history = self.env['ora.call.history'].log_call_status(status_payload)
        self.assertTrue(history)
        self.assertEqual(history.vapi_call_id, 'call_abc_123')
        self.assertEqual(history.call_type, 'webCall')
        self.assertEqual(history.duration, 150)
        self.assertEqual(history.cost, 0.125)
        self.assertIn('Customer: Hello', history.transcript)

        # Update to completed
        end_payload = {
            'call_id': 'call_abc_123',
            'message': {
                'type': 'end-of-call-report',
                'call': {
                    'id': 'call_abc_123',
                    'type': 'webCall',
                    'cost': 0.150,
                },
                'recordingUrl': 'https://vapi.ai/recordings/call_abc_123.mp3',
            }
        }
        updated = self.env['ora.call.history'].log_call_status(end_payload)
        self.assertEqual(updated.id, history.id)
        self.assertEqual(updated.status, 'completed')
        self.assertEqual(updated.recording_url, 'https://vapi.ai/recordings/call_abc_123.mp3')

    def test_06_webhook_order_creation_webcall(self):
        """Test web call sale order generation and auto-confirm toggle."""
        self.env['ir.config_parameter'].sudo().set_str('ora_ai_base.voice_order_auto_confirm', 'True')
        from odoo.addons.ora_ai_base.controllers.ora_ai_base import VapiAssistant
        controller = VapiAssistant()

        # Mock request data
        mock_payload = {
            'message': {
                'call': {
                    'id': 'call_web_order_999',
                    'type': 'webCall',
                },
                'toolCalls': [{
                    'id': 'tool_call_001',
                    'function': {
                        'name': 'GetFinalOrderDetails',
                        'arguments': {
                            'OrderDetails': {
                                'Products': [{
                                    'Customer': 'Alice Web',
                                    'Product': 'Iced Latte',
                                    'productId': self.product.id,
                                    'Quantity': 2,
                                    'Variant': '-'
                                }]
                            }
                        }
                    }
                }]
            }
        }

        with patch.object(controller, '_parse_request_data', return_value=mock_payload), \
             patch.object(controller, '_verify_webhook_secret', return_value=True):
            res = controller.final_details()
            self.assertIn('results', res)
            self.assertIn('successfully created', res['results'][0]['result'])

        # Verify sale order
        order = self.env['sale.order'].search([('partner_id.name', '=', 'Alice Web')], limit=1)
        self.assertTrue(order)
        self.assertEqual(len(order.order_line), 1)
        self.assertEqual(order.order_line[0].product_id.id, self.product.id)
        self.assertEqual(order.order_line[0].product_uom_qty, 2)
        self.assertEqual(order.state, 'sale')  # auto-confirmed

        # Verify linked call history
        history = self.env['ora.call.history'].search([('vapi_call_id', '=', 'call_web_order_999')], limit=1)
        self.assertTrue(history)
        self.assertEqual(history.order_id.id, order.id)
        self.assertEqual(history.partner_id.id, order.partner_id.id)

    def test_07_webhook_idempotency(self):
        """Test duplicate webhook payload does not create duplicate sale orders."""
        from odoo.addons.ora_ai_base.controllers.ora_ai_base import VapiAssistant
        controller = VapiAssistant()

        mock_payload = {
            'message': {
                'call': {
                    'id': 'call_idempotent_test',
                    'type': 'webCall',
                },
                'toolCalls': [{
                    'id': 'tool_call_idem',
                    'function': {
                        'name': 'GetFinalOrderDetails',
                        'arguments': {
                            'OrderDetails': {
                                'Products': [{
                                    'Customer': 'Bob Idempotent',
                                    'Product': 'Iced Latte',
                                    'productId': self.product.id,
                                    'Quantity': 1,
                                    'Variant': '-'
                                }]
                            }
                        }
                    }
                }]
            }
        }

        with patch.object(controller, '_parse_request_data', return_value=mock_payload), \
             patch.object(controller, '_verify_webhook_secret', return_value=True):
            res1 = controller.final_details()
            self.assertIn('successfully created', res1['results'][0]['result'])

            # Second identical call
            res2 = controller.final_details()
            self.assertIn('already placed', res2['results'][0]['result'])

        orders = self.env['sale.order'].search([('partner_id.name', '=', 'Bob Idempotent')])
        self.assertEqual(len(orders), 1)

