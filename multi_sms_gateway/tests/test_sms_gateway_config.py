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
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#############################################################################
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', 'at_install')
class TestSmsGatewayConfig(TransactionCase):
    """Test suite for sms.gateway.config model and constraints."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vonage_gateway = cls.env.ref('multi_sms_gateway.sms_gateway_vonage')
        cls.twilio_gateway = cls.env.ref('multi_sms_gateway.sms_gateway_twilio')
        cls.telesign_gateway = cls.env.ref('multi_sms_gateway.sms_gateway_telesign')

    def test_create_vonage_config_success(self):
        """Create valid Vonage gateway configuration."""
        config = self.env['sms.gateway.config'].create({
            'sms_gateway_id': self.vonage_gateway.id,
            'vonage_key': 'test_vonage_key',
            'vonage_secret': 'test_vonage_secret',
        })
        self.assertEqual(config.gateway_name, 'Vonage')
        self.assertEqual(config.vonage_key, 'test_vonage_key')
        self.assertEqual(config.vonage_secret, 'test_vonage_secret')

    def test_create_vonage_config_missing_key(self):
        """Creating Vonage config without API key raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.env['sms.gateway.config'].create({
                'sms_gateway_id': self.vonage_gateway.id,
                'vonage_secret': 'test_vonage_secret',
            })

    def test_create_vonage_config_missing_secret(self):
        """Creating Vonage config without API secret raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.env['sms.gateway.config'].create({
                'sms_gateway_id': self.vonage_gateway.id,
                'vonage_key': 'test_vonage_key',
            })

    def test_create_twilio_config_success(self):
        """Create valid Twilio gateway configuration."""
        config = self.env['sms.gateway.config'].create({
            'sms_gateway_id': self.twilio_gateway.id,
            'twilio_account_sid': 'TEST_TWILIO_ACCOUNT_SID',
            'twilio_auth_token': 'test_auth_token',
            'twilio_phone_number': '+17372508034',
        })
        self.assertEqual(config.gateway_name, 'Twilio')
        self.assertEqual(config.twilio_phone_number, '+17372508034')

    def test_create_twilio_config_missing_phone(self):
        """Creating Twilio config without phone number raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.env['sms.gateway.config'].create({
                'sms_gateway_id': self.twilio_gateway.id,
                'twilio_account_sid': 'AC1234567890',
                'twilio_auth_token': 'test_token',
            })

    def test_create_twilio_config_missing_token(self):
        """Creating Twilio config without auth token raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.env['sms.gateway.config'].create({
                'sms_gateway_id': self.twilio_gateway.id,
                'twilio_account_sid': 'AC1234567890',
                'twilio_phone_number': '+17372508034',
            })

    def test_create_twilio_config_missing_sid(self):
        """Creating Twilio config without account SID raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.env['sms.gateway.config'].create({
                'sms_gateway_id': self.twilio_gateway.id,
                'twilio_auth_token': 'test_token',
                'twilio_phone_number': '+17372508034',
            })

    def test_create_telesign_config_success(self):
        """Create valid TeleSign gateway configuration."""
        config = self.env['sms.gateway.config'].create({
            'sms_gateway_id': self.telesign_gateway.id,
            'telesign_customer': '12345678-1234-1234-1234-123456789012',
            'telesign_api_key': 'test_telesign_api_key',
        })
        self.assertEqual(config.gateway_name, 'TeleSign')
        self.assertEqual(config.gateway_provider, 'telesign')
        self.assertEqual(
            config.telesign_customer, '12345678-1234-1234-1234-123456789012'
        )

    def test_create_telesign_config_missing_customer(self):
        """Creating TeleSign config without customer ID raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.env['sms.gateway.config'].create({
                'sms_gateway_id': self.telesign_gateway.id,
                'telesign_api_key': 'test_telesign_api_key',
            })

    def test_create_telesign_config_missing_api_key(self):
        """Creating TeleSign config without API key raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.env['sms.gateway.config'].create({
                'sms_gateway_id': self.telesign_gateway.id,
                'telesign_customer': '12345678-1234-1234-1234-123456789012',
            })

    def test_create_other_gateway_config(self):
        """Other/custom gateway without specific credentials passes validation."""
        other_gateway = self.env['sms.gateway'].create({'name': 'CustomOther'})
        config = self.env['sms.gateway.config'].create({
            'sms_gateway_id': other_gateway.id,
        })
        self.assertEqual(config.gateway_name, 'CustomOther')
