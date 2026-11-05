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
from unittest.mock import patch, MagicMock
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

        self.assertEqual(ICP.get_str('ora_ai_base.vapi_private_api_key'), 'test_priv_key_123')
        self.assertEqual(ICP.get_str('ora_ai_base.vapi_public_api_key'), 'test_pub_key_456')
        self.assertEqual(ICP.get_str('ora_ai_base.voice_order_auto_confirm'), 'True')

    def test_02_prompt_generation_and_currency(self):
        """Test prompt computation includes company name, currency symbol, customer name instruction, and product prices."""
        self.assistant._compute_prompt()
        prompt = self.assistant.prompt
        self.assertIn(self.company.name, prompt)
        self.assertIn(self.company.currency_id.symbol, prompt)
        self.assertIn('Iced Latte', prompt)
        self.assertIn(f"{self.product.list_price:.2f}", prompt)
        self.assertIn("What is the customer's name?", prompt)
        self.assertIn("NEVER ask 'What is your name?'", prompt)
        self.assertIn("The person talking to you is the SALESPERSON", prompt)
        self.assertIn("The sales order for customer [Customer Name] has been successfully created. Goodbye!", prompt)
        self.assertIn("NEVER say 'Thank you for ordering, [Customer Name]'", prompt)

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

        mock_req = MagicMock()
        mock_req.env = self.env
        mock_req.params = {}
        mock_req.user = self.env.user

        with patch('odoo.addons.ora_ai_base.controllers.ora_ai_base.request', mock_req), \
             patch.object(controller, '_parse_request_data', return_value=mock_payload), \
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

        mock_req = MagicMock()
        mock_req.env = self.env
        mock_req.params = {}
        mock_req.user = self.env.user

        with patch('odoo.addons.ora_ai_base.controllers.ora_ai_base.request', mock_req), \
             patch.object(controller, '_parse_request_data', return_value=mock_payload), \
             patch.object(controller, '_verify_webhook_secret', return_value=True):
            res1 = controller.final_details()
            self.assertIn('successfully created', res1['results'][0]['result'])

            # Second identical call
            res2 = controller.final_details()
            self.assertIn('already placed', res2['results'][0]['result'])

        orders = self.env['sale.order'].search([('partner_id.name', '=', 'Bob Idempotent')])
        self.assertEqual(len(orders), 1)

    def test_08_existing_customer_matching_and_conditional_creation(self):
        """Test matching existing customer without duplicating, and creating new only when not found."""
        from odoo.addons.ora_ai_base.controllers.ora_ai_base import VapiAssistant
        controller = VapiAssistant()

        # 1. Existing customer in database
        existing_partner = self.env['res.partner'].create({
            'name': 'Charlie Existing',
            'email': 'charlie@existing.com',
        })

        # Order for existing customer by spoken name
        mock_payload_existing = {
            'message': {
                'call': {
                    'id': 'call_match_existing',
                    'type': 'webCall',
                },
                'toolCalls': [{
                    'id': 'tool_call_match',
                    'function': {
                        'name': 'GetFinalOrderDetails',
                        'arguments': {
                            'OrderDetails': {
                                'Products': [{
                                    'Customer': 'charlie existing',  # case-insensitive
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

        mock_req = MagicMock()
        mock_req.env = self.env
        mock_req.params = {}
        mock_req.user = self.env.user

        with patch('odoo.addons.ora_ai_base.controllers.ora_ai_base.request', mock_req), \
             patch.object(controller, '_parse_request_data', return_value=mock_payload_existing), \
             patch.object(controller, '_verify_webhook_secret', return_value=True):
            res = controller.final_details()
            self.assertIn('successfully created', res['results'][0]['result'])

        # Verify sale order used existing partner and did not create duplicate
        order_existing = self.env['sale.order'].search([('partner_id', '=', existing_partner.id)], limit=1)
        self.assertTrue(order_existing)
        partner_count = self.env['res.partner'].search_count([('name', '=ilike', 'Charlie Existing')])
        self.assertEqual(partner_count, 1, "Must not create duplicate partner for existing customer")

        # 2. Order for a brand new customer
        mock_payload_new = {
            'message': {
                'call': {
                    'id': 'call_create_new_cust',
                    'type': 'webCall',
                },
                'toolCalls': [{
                    'id': 'tool_call_new_cust',
                    'function': {
                        'name': 'GetFinalOrderDetails',
                        'arguments': {
                            'OrderDetails': {
                                'Products': [{
                                    'Customer': 'David BrandNew99',
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

        with patch('odoo.addons.ora_ai_base.controllers.ora_ai_base.request', mock_req), \
             patch.object(controller, '_parse_request_data', return_value=mock_payload_new), \
             patch.object(controller, '_verify_webhook_secret', return_value=True):
            res_new = controller.final_details()
            self.assertIn('successfully created', res_new['results'][0]['result'])

        # Verify new partner was created
        new_partner = self.env['res.partner'].search([('name', '=', 'David BrandNew99')], limit=1)
        self.assertTrue(new_partner, "Must create new partner when customer does not exist")
        order_new = self.env['sale.order'].search([('partner_id', '=', new_partner.id)], limit=1)
        self.assertTrue(order_new)

    def test_09_salesperson_assignment_from_logged_in_user(self):
        """Test salesperson user_id is assigned to Sale Order and Call History from logged-in user."""
        from odoo.addons.ora_ai_base.controllers.ora_ai_base import VapiAssistant
        controller = VapiAssistant()

        salesperson = self.env['res.users'].create({
            'name': 'Sales Rep Alice',
            'login': 'rep_alice',
            'email': 'alice@example.com',
        })

        mock_payload = {
            'message': {
                'call': {
                    'id': 'call_salesperson_test_101',
                    'type': 'webCall',
                    'assistantOverrides': {
                        'variableValues': {
                            'salesperson_id': str(salesperson.id),
                        }
                    }
                },
                'toolCalls': [{
                    'id': 'tool_call_salesperson',
                    'function': {
                        'name': 'GetFinalOrderDetails',
                        'arguments': {
                            'OrderDetails': {
                                'Products': [{
                                    'Customer': 'Customer For Alice',
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

        mock_req = MagicMock()
        mock_req.env = self.env
        mock_req.params = {}
        mock_req.user = self.env.user

        with patch('odoo.addons.ora_ai_base.controllers.ora_ai_base.request', mock_req), \
             patch.object(controller, '_parse_request_data', return_value=mock_payload), \
             patch.object(controller, '_verify_webhook_secret', return_value=True):
            res = controller.final_details()
            self.assertIn('successfully created', res['results'][0]['result'])

        # Verify created Sale Order has salesperson set
        order = self.env['sale.order'].search([('partner_id.name', '=', 'Customer For Alice')], limit=1)
        self.assertTrue(order)
        self.assertEqual(order.user_id.id, salesperson.id, "Sale order salesperson must match logged-in user")

        # Verify Call History has salesperson set
        call_history = self.env['ora.call.history'].search([('vapi_call_id', '=', 'call_salesperson_test_101')], limit=1)
        self.assertTrue(call_history)
        self.assertEqual(call_history.user_id.id, salesperson.id, "Call history salesperson must match logged-in user")

    def test_10_check_customer_found(self):
        """Test CheckCustomerExists returns FOUND when customer exists in database."""
        from odoo.addons.ora_ai_base.controllers.ora_ai_base import VapiAssistant
        controller = VapiAssistant()

        existing_partner = self.env['res.partner'].create({
            'name': 'Sophia Searchable',
            'email': 'sophia@example.com',
        })

        mock_payload = {
            'message': {
                'toolCalls': [{
                    'id': 'tool_call_chk_1',
                    'function': {
                        'name': 'CheckCustomerExists',
                        'arguments': {
                            'customer_name': 'Sophia Searchable'
                        }
                    }
                }]
            }
        }

        mock_req = MagicMock()
        mock_req.env = self.env
        mock_req.params = {}

        with patch('odoo.addons.ora_ai_base.controllers.ora_ai_base.request', mock_req), \
             patch.object(controller, '_parse_request_data', return_value=mock_payload), \
             patch.object(controller, '_verify_webhook_secret', return_value=True):
            res = controller.check_customer()
            tool_res = res['results'][0]['result']
            self.assertIn("FOUND", tool_res)
            self.assertIn(str(existing_partner.id), tool_res)
            self.assertIn("Sophia Searchable", tool_res)

        # Also test with speech-to-text trailing punctuation: "Sophia Searchable."
        mock_payload['message']['toolCalls'][0]['function']['arguments']['customer_name'] = "Sophia Searchable."
        with patch('odoo.addons.ora_ai_base.controllers.ora_ai_base.request', mock_req), \
             patch.object(controller, '_parse_request_data', return_value=mock_payload), \
             patch.object(controller, '_verify_webhook_secret', return_value=True):
            res_punct = controller.check_customer()
            self.assertIn("FOUND", res_punct['results'][0]['result'])

    def test_11_check_customer_not_found(self):
        """Test CheckCustomerExists returns NOT FOUND and asks to create new account when absent."""
        from odoo.addons.ora_ai_base.controllers.ora_ai_base import VapiAssistant
        controller = VapiAssistant()

        mock_payload = {
            'message': {
                'toolCalls': [{
                    'id': 'tool_call_chk_2',
                    'function': {
                        'name': 'CheckCustomerExists',
                        'arguments': {
                            'customer_name': 'Totally NonExistent Person 999'
                        }
                    }
                }]
            }
        }

        mock_req = MagicMock()
        mock_req.env = self.env
        mock_req.params = {}

        with patch('odoo.addons.ora_ai_base.controllers.ora_ai_base.request', mock_req), \
             patch.object(controller, '_parse_request_data', return_value=mock_payload), \
             patch.object(controller, '_verify_webhook_secret', return_value=True):
            res = controller.check_customer()
            tool_res = res['results'][0]['result']
            self.assertIn("NOT FOUND", tool_res)
            self.assertIn("create a new customer account", tool_res)

    def test_12_salesperson_fallback_to_partner(self):
        """Test that if caller passes no salesperson, order falls back to partner's assigned salesperson."""
        from odoo.addons.ora_ai_base.controllers.ora_ai_base import VapiAssistant
        controller = VapiAssistant()

        salesperson_bob = self.env['res.users'].create({
            'name': 'Sales Rep Bob',
            'login': 'rep_bob',
            'email': 'bob@example.com',
        })
        partner_with_salesperson = self.env['res.partner'].create({
            'name': 'Corporate Client Bob',
            'user_id': salesperson_bob.id,
        })

        mock_payload = {
            'message': {
                'call': {
                    'id': 'call_fallback_bob_999',
                    'type': 'webCall',
                },
                'toolCalls': [{
                    'id': 'tool_call_fallback',
                    'function': {
                        'name': 'GetFinalOrderDetails',
                        'arguments': {
                            'OrderDetails': {
                                'Products': [{
                                    'Customer': 'Corporate Client Bob',
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

        mock_req = MagicMock()
        mock_req.env = self.env
        mock_req.params = {}
        mock_req.user = self.env.ref('base.public_user')

        with patch('odoo.addons.ora_ai_base.controllers.ora_ai_base.request', mock_req), \
             patch.object(controller, '_parse_request_data', return_value=mock_payload), \
             patch.object(controller, '_verify_webhook_secret', return_value=True):
            res = controller.final_details()
            self.assertIn('successfully created', res['results'][0]['result'])

        order = self.env['sale.order'].search([('partner_id', '=', partner_with_salesperson.id)], limit=1)
        self.assertTrue(order)
        self.assertEqual(order.user_id.id, salesperson_bob.id, "Order should fall back to partner's assigned salesperson")

    def test_13_order_requires_customer_selection(self):
        """Test that sale order creation is rejected if customer is completely unspecified."""
        from odoo.addons.ora_ai_base.controllers.ora_ai_base import VapiAssistant
        controller = VapiAssistant()

        mock_payload = {
            'message': {
                'call': {
                    'id': 'call_no_customer_123',
                    'type': 'webCall',
                },
                'toolCalls': [{
                    'id': 'tool_call_no_cust',
                    'function': {
                        'name': 'GetFinalOrderDetails',
                        'arguments': {
                            'OrderDetails': {
                                'Products': [{
                                    'Customer': '',
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

        mock_req = MagicMock()
        mock_req.env = self.env
        mock_req.params = {}
        mock_req.user = self.env.ref('base.public_user')

        with patch('odoo.addons.ora_ai_base.controllers.ora_ai_base.request', mock_req), \
             patch.object(controller, '_parse_request_data', return_value=mock_payload), \
             patch.object(controller, '_verify_webhook_secret', return_value=True):
            res = controller.final_details()
            result_str = res['results'][0]['result']
            self.assertIn("only supported after the customer has been identified or selected", result_str)

        # Verify no sale order was created for this call
        call_hist = self.env['ora.call.history'].search([('vapi_call_id', '=', 'call_no_customer_123')], limit=1)
        self.assertFalse(call_hist and call_hist.order_id)

