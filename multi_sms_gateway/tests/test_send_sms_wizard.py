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
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', 'at_install')
class TestSendSmsWizard(TransactionCase):
    """Comprehensive test suite for send.sms wizard model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_us = cls.env.ref('base.us')

        cls.gateway_vonage = cls.env.ref('multi_sms_gateway.sms_gateway_vonage')
        cls.config_vonage = cls.env['sms.gateway.config'].create({
            'sms_gateway_id': cls.gateway_vonage.id,
            'vonage_key': 'test_vonage_key',
            'vonage_secret': 'test_vonage_secret',
        })

        cls.gateway_twilio = cls.env.ref('multi_sms_gateway.sms_gateway_twilio')
        cls.config_twilio = cls.env['sms.gateway.config'].create({
            'sms_gateway_id': cls.gateway_twilio.id,
            'twilio_account_sid': 'TEST_TWILIO_ACCOUNT_SID',
            'twilio_auth_token': 'test_auth_token',
            'twilio_phone_number': '+17372508034',
        })

        cls.gateway_telesign = cls.env.ref('multi_sms_gateway.sms_gateway_telesign')
        cls.config_telesign = cls.env['sms.gateway.config'].create({
            'sms_gateway_id': cls.gateway_telesign.id,
            'telesign_customer': '12345678-1234-1234-1234-123456789012',
            'telesign_api_key': 'test_telesign_api_key',
        })

    def test_default_get_context(self):
        """Wizard correctly populates defaults from context keys."""
        context = {
            'default_gateway_config_id': self.config_twilio.id,
            'default_recipient_numbers': '+12025550100',
            'default_message_text': 'Standard context test message',
        }
        defaults = self.env['send.sms'].with_context(**context).default_get([
            'gateway_config_id', 'recipient_numbers', 'message_text'
        ])
        self.assertEqual(defaults.get('gateway_config_id'), self.config_twilio.id)
        self.assertEqual(defaults.get('recipient_numbers'), '+12025550100')
        self.assertEqual(defaults.get('message_text'), 'Standard context test message')

    def test_create_standard_fields(self):
        """Wizard creates with standard fields successfully."""
        wizard = self.env['send.sms'].create({
            'gateway_config_id': self.config_twilio.id,
            'recipient_numbers': '+12025550101',
            'message_text': 'Standard creation test',
        })
        self.assertEqual(wizard.gateway_config_id, self.config_twilio)
        self.assertEqual(wizard.recipient_numbers, '+12025550101')
        self.assertEqual(wizard.message_text, 'Standard creation test')

    def test_validation_errors(self):
        """Test validation guards in action_send_sms."""
        # Missing gateway config
        wizard_no_gateway = self.env['send.sms'].new({
            'gateway_config_id': False,
            'recipient_numbers': '+12025550102',
            'message_text': 'Validation test',
        })
        with self.assertRaises(UserError):
            wizard_no_gateway.action_send_sms()

        # Missing recipients
        wizard_no_recipients = self.env['send.sms'].new({
            'gateway_config_id': self.config_twilio.id,
            'recipient_numbers': '   ',
            'message_text': 'Validation test',
        })
        with self.assertRaises(UserError):
            wizard_no_recipients.action_send_sms()

        # No valid phone numbers parsed
        wizard_invalid_recipients = self.env['send.sms'].new({
            'gateway_config_id': self.config_twilio.id,
            'recipient_numbers': ', , ,, ',
            'message_text': 'Validation test',
        })
        with self.assertRaises(UserError):
            wizard_invalid_recipients.action_send_sms()

    def test_unsupported_gateway_error(self):
        """Action raises UserError for unsupported gateway provider."""
        other_gateway = self.env['sms.gateway'].create({'name': 'UnknownProvider'})
        other_config = self.env['sms.gateway.config'].create({
            'sms_gateway_id': other_gateway.id
        })
        wizard = self.env['send.sms'].create({
            'gateway_config_id': other_config.id,
            'recipient_numbers': '+12025550103',
            'message_text': 'Unsupported gateway test',
        })
        with self.assertRaises(UserError):
            wizard.action_send_sms()

    def test_normalize_phone_number_cases(self):
        """Test phone number normalization cases including edge cases."""
        wizard = self.env['send.sms'].create({
            'gateway_config_id': self.config_twilio.id,
            'recipient_numbers': '+12025550104',
            'message_text': 'Normalization test',
        })

        # Empty / non-string
        self.assertFalse(wizard._normalize_phone_number(''))
        self.assertFalse(wizard._normalize_phone_number(None))

        # Standard E.164
        self.assertEqual(wizard._normalize_phone_number('+12025550104'), '+12025550104')

        # Formatting with country
        res = wizard._normalize_phone_number('2025550104', country=self.country_us)
        self.assertEqual(res, '+12025550104')

        # Leading trunk 0 stripping
        res = wizard._normalize_phone_number('02025550104', country=self.country_us)
        self.assertEqual(res, '+12025550104')

        # Fallback with raw digits
        res = wizard._normalize_phone_number('+1 (202) 555-0104')
        self.assertEqual(res, '+12025550104')

    def test_get_recipient_phone_numbers_parsing(self):
        """Parsing comma-separated phone numbers returns list of normalized numbers."""
        partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'country_id': self.country_us.id,
        })
        wizard = self.env['send.sms'].with_context(
            active_model='res.partner', active_id=partner.id
        ).create({
            'gateway_config_id': self.config_twilio.id,
            'recipient_numbers': '+12025550105, 2025550106, +1-202-555-0107',
            'message_text': 'Multi-recipient test',
        })
        numbers = wizard._get_recipient_phone_numbers()
        self.assertIn('+12025550105', numbers)
        self.assertIn('+12025550106', numbers)
        self.assertIn('+12025550107', numbers)

    @patch('odoo.addons.multi_sms_gateway.wizard.send_sms.Vonage')
    @patch('odoo.addons.multi_sms_gateway.wizard.send_sms.Auth')
    @patch('odoo.addons.multi_sms_gateway.wizard.send_sms.Sms')
    def test_send_via_vonage_success(self, mock_sms, mock_auth, mock_vonage):
        """Successful SMS sending via Vonage creates history and returns notification."""
        mock_client = MagicMock()
        mock_vonage.return_value = mock_client

        partner = self.env['res.partner'].create({
            'name': 'Vonage Partner',
            'phone': '+12025550110',
        })
        wizard = self.env['send.sms'].with_context(
            active_model='res.partner', active_id=partner.id
        ).create({
            'gateway_config_id': self.config_vonage.id,
            'recipient_numbers': '+12025550110',
            'message_text': 'Vonage test message',
        })

        action = wizard.action_send_sms()
        self.assertEqual(action.get('type'), 'ir.actions.client')
        self.assertEqual(action.get('tag'), 'display_notification')
        self.assertEqual(action.get('params', {}).get('type'), 'success')

        # Check history record created
        history = self.env['sms.history'].search([
            ('sms_mobile', '=', '+12025550110')
        ])
        self.assertTrue(history)
        self.assertEqual(history.sms_text, 'Vonage test message')
        self.assertEqual(history.sms_gateway_id, self.gateway_vonage)

    @patch('odoo.addons.multi_sms_gateway.wizard.send_sms.Vonage', None)
    def test_send_via_vonage_library_missing(self):
        """Vonage send raises UserError when library is missing."""
        wizard = self.env['send.sms'].create({
            'gateway_config_id': self.config_vonage.id,
            'recipient_numbers': '+12025550111',
            'message_text': 'Missing vonage test',
        })
        with self.assertRaises(UserError):
            wizard.action_send_sms()

    @patch('odoo.addons.multi_sms_gateway.wizard.send_sms.Vonage')
    def test_send_via_vonage_client_error(self, mock_vonage):
        """Vonage client initialization failure raises UserError."""
        mock_vonage.side_effect = Exception("Auth Failure")
        wizard = self.env['send.sms'].create({
            'gateway_config_id': self.config_vonage.id,
            'recipient_numbers': '+12025550112',
            'message_text': 'Vonage auth failure test',
        })
        with self.assertRaises(UserError):
            wizard.action_send_sms()

    @patch('odoo.addons.multi_sms_gateway.wizard.send_sms.Vonage')
    @patch('odoo.addons.multi_sms_gateway.wizard.send_sms.Auth')
    @patch('odoo.addons.multi_sms_gateway.wizard.send_sms.Sms')
    def test_send_via_vonage_send_error(self, mock_sms, mock_auth, mock_vonage):
        """Vonage message sending failure raises UserError."""
        mock_client = MagicMock()
        mock_client.messages.send.side_effect = Exception("Network timeout")
        mock_vonage.return_value = mock_client

        wizard = self.env['send.sms'].create({
            'gateway_config_id': self.config_vonage.id,
            'recipient_numbers': '+12025550113',
            'message_text': 'Vonage send error test',
        })
        with self.assertRaises(UserError):
            wizard.action_send_sms()

    @patch('odoo.addons.multi_sms_gateway.wizard.send_sms.Client')
    def test_send_via_twilio_success(self, mock_client_cls):
        """Successful SMS sending via Twilio creates history record."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        wizard = self.env['send.sms'].create({
            'gateway_config_id': self.config_twilio.id,
            'recipient_numbers': '+12025550120',
            'message_text': 'Twilio test message',
        })

        action = wizard.action_send_sms()
        self.assertEqual(action.get('type'), 'ir.actions.client')
        self.assertEqual(action.get('tag'), 'display_notification')

        history = self.env['sms.history'].search([
            ('sms_mobile', '=', '+12025550120')
        ])
        self.assertTrue(history)
        self.assertEqual(history.sms_text, 'Twilio test message')

    @patch('odoo.addons.multi_sms_gateway.wizard.send_sms.Client', None)
    def test_send_via_twilio_library_missing(self):
        """Twilio send raises UserError when library is missing."""
        wizard = self.env['send.sms'].create({
            'gateway_config_id': self.config_twilio.id,
            'recipient_numbers': '+12025550121',
            'message_text': 'Missing twilio test',
        })
        with self.assertRaises(UserError):
            wizard.action_send_sms()

    @patch('odoo.addons.multi_sms_gateway.wizard.send_sms.Client')
    def test_send_via_twilio_client_error(self, mock_client_cls):
        """Twilio client initialization failure raises UserError."""
        mock_client_cls.side_effect = Exception("Twilio credentials invalid")
        wizard = self.env['send.sms'].create({
            'gateway_config_id': self.config_twilio.id,
            'recipient_numbers': '+12025550122',
            'message_text': 'Twilio init error test',
        })
        with self.assertRaises(UserError):
            wizard.action_send_sms()

    @patch('odoo.addons.multi_sms_gateway.wizard.send_sms.Client')
    def test_send_via_twilio_trial_errors(self, mock_client_cls):
        """Twilio trial errors (template and unverified recipient) raise UserError."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        wizard = self.env['send.sms'].create({
            'gateway_config_id': self.config_twilio.id,
            'recipient_numbers': '+12025550123',
            'message_text': 'Twilio trial error test',
        })

        # Trial template error code 572006
        err_template = Exception("Predefined sms templates required")
        err_template.code = 572006
        mock_client.messages.create.side_effect = err_template
        with self.assertRaises(UserError):
            wizard.action_send_sms()

        # Trial unverified recipient error code 21608
        err_unverified = Exception("Recipient number is not verified")
        err_unverified.code = 21608
        mock_client.messages.create.side_effect = err_unverified
        with self.assertRaises(UserError):
            wizard.action_send_sms()

    @patch('odoo.addons.multi_sms_gateway.wizard.send_sms.MessagingClient')
    def test_send_via_telesign_success(self, mock_telesign_cls):
        """Successful SMS sending via TeleSign."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json = {'status': {'code': 200, 'description': 'Delivered'}}
        mock_response.ok = True
        mock_client.message.return_value = mock_response
        mock_telesign_cls.return_value = mock_client

        wizard = self.env['send.sms'].create({
            'gateway_config_id': self.config_telesign.id,
            'recipient_numbers': '+12025550130',
            'message_text': 'TeleSign test message',
        })

        action = wizard.action_send_sms()
        self.assertEqual(action.get('type'), 'ir.actions.client')

        history = self.env['sms.history'].search([
            ('sms_mobile', '=', '+12025550130')
        ])
        self.assertTrue(history)
        self.assertEqual(history.sms_text, 'TeleSign test message')

    @patch('odoo.addons.multi_sms_gateway.wizard.send_sms.MessagingClient', None)
    def test_send_via_telesign_library_missing(self):
        """TeleSign send raises UserError when library is missing."""
        wizard = self.env['send.sms'].create({
            'gateway_config_id': self.config_telesign.id,
            'recipient_numbers': '+12025550131',
            'message_text': 'Missing telesign test',
        })
        with self.assertRaises(UserError):
            wizard.action_send_sms()

    @patch('odoo.addons.multi_sms_gateway.wizard.send_sms.MessagingClient')
    def test_send_via_telesign_client_error(self, mock_telesign_cls):
        """TeleSign client initialization failure raises UserError."""
        mock_telesign_cls.side_effect = Exception("TeleSign auth failure")
        wizard = self.env['send.sms'].create({
            'gateway_config_id': self.config_telesign.id,
            'recipient_numbers': '+12025550132',
            'message_text': 'TeleSign init error test',
        })
        with self.assertRaises(UserError):
            wizard.action_send_sms()

    @patch('odoo.addons.multi_sms_gateway.wizard.send_sms.MessagingClient')
    def test_send_via_telesign_status_errors(self, mock_telesign_cls):
        """TeleSign error responses (11000, 10033, 10008, generic) raise UserError."""
        mock_client = MagicMock()
        mock_telesign_cls.return_value = mock_client

        wizard = self.env['send.sms'].create({
            'gateway_config_id': self.config_telesign.id,
            'recipient_numbers': '+12025550133',
            'message_text': 'TeleSign error codes test',
        })

        # Error 11000: Invalid phone number
        resp = MagicMock()
        resp.json = {'status': {'code': 11000, 'description': 'Invalid phone number'}}
        resp.ok = False
        mock_client.message.return_value = resp
        with self.assertRaises(UserError):
            wizard.action_send_sms()

        # Error 10033: Unverified trial recipient
        resp.json = {
            'status': {
                'code': 10033,
                'description': 'Phone number has not been verified',
            }
        }
        with self.assertRaises(UserError):
            wizard.action_send_sms()

        # Error 10008: Invalid Signature
        resp.json = {'status': {'code': 10008, 'description': 'Invalid signature'}}
        with self.assertRaises(UserError):
            wizard.action_send_sms()

        # Generic error
        resp.json = {'status': {'code': 50000, 'description': 'Server Error'}}
        with self.assertRaises(UserError):
            wizard.action_send_sms()

    def test_post_chatter_notification_multi_partners(self):
        """Chatter notification is posted to all selected partner records."""
        partner1 = self.env['res.partner'].create({
            'name': 'Chatter Partner 1',
            'phone': '+12025550141',
        })
        partner2 = self.env['res.partner'].create({
            'name': 'Chatter Partner 2',
            'phone': '+12025550142',
        })

        wizard = self.env['send.sms'].with_context(
            active_model='res.partner',
            active_ids=[partner1.id, partner2.id],
        ).create({
            'gateway_config_id': self.config_twilio.id,
            'recipient_numbers': '+12025550141, +12025550142',
            'message_text': 'Multi chatter post test',
        })

        wizard._post_chatter_notification()

        msgs1 = partner1.message_ids.filtered(
            lambda m: 'Multi chatter post test' in (m.body or '')
        )
        msgs2 = partner2.message_ids.filtered(
            lambda m: 'Multi chatter post test' in (m.body or '')
        )
        self.assertTrue(msgs1)
        self.assertTrue(msgs2)
