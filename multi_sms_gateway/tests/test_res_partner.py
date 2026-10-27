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
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', 'at_install')
class TestResPartner(TransactionCase):
    """Test suite for res.partner send_sms action method."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_us = cls.env.ref('base.us')
        cls.gateway_twilio = cls.env.ref('multi_sms_gateway.sms_gateway_twilio')
        cls.config_twilio = cls.env['sms.gateway.config'].create({
            'sms_gateway_id': cls.gateway_twilio.id,
            'twilio_account_sid': 'TEST_TWILIO_ACCOUNT_SID',
            'twilio_auth_token': 'test_auth_token',
            'twilio_phone_number': '+17372508034',
        })

    def test_send_sms_partner_e164(self):
        """Action returns wizard prefilled with partner's E.164 phone number."""
        partner = self.env['res.partner'].create({
            'name': 'Alice E164',
            'phone': '+12025550143',
            'country_id': self.country_us.id,
        })
        action = partner.send_sms()
        self.assertEqual(action.get('type'), 'ir.actions.act_window')
        self.assertEqual(action.get('res_model'), 'send.sms')
        self.assertEqual(action.get('target'), 'new')
        self.assertEqual(action.get('view_mode'), 'form')
        ctx = action.get('context', {})
        self.assertIn('+12025550143', ctx.get('default_recipient_numbers'))
        self.assertEqual(
            ctx.get('default_gateway_config_id'), self.config_twilio.id
        )

    def test_send_sms_partner_local_number(self):
        """Action formats local number using country phone code."""
        partner = self.env['res.partner'].create({
            'name': 'Charlie Local',
            'phone': '2025550199',
            'country_id': self.country_us.id,
        })
        action = partner.send_sms()
        ctx = action.get('context', {})
        self.assertIn('+12025550199', ctx.get('default_recipient_numbers'))

    def test_send_sms_partner_local_with_country_code_prefix(self):
        """Action prefixes '+' when local number already has country code digits."""
        partner = self.env['res.partner'].create({
            'name': 'Diana Digits',
            'phone': '12025550155',
            'country_id': self.country_us.id,
        })
        action = partner.send_sms()
        ctx = action.get('context', {})
        self.assertIn('+12025550155', ctx.get('default_recipient_numbers'))

    def test_send_sms_multiple_partners(self):
        """Action aggregates phone numbers from multiple partners in active_ids."""
        partner1 = self.env['res.partner'].create({
            'name': 'Multi 1',
            'phone': '+12025550111',
        })
        partner2 = self.env['res.partner'].create({
            'name': 'Multi 2',
            'phone': '+12025550222',
        })
        action = self.env['res.partner'].with_context(
            active_ids=[partner1.id, partner2.id]
        ).send_sms()
        recipients = action.get('context', {}).get(
            'default_recipient_numbers', ''
        ).split(',')
        self.assertIn('+12025550111', recipients)
        self.assertIn('+12025550222', recipients)

    def test_send_sms_partner_phone_validation_success(self):
        """Action uses phone_validation.phone_format when it returns formatted E.164."""
        partner = self.env['res.partner'].create({
            'name': 'Validation Success',
            'phone': '2025550177',
            'country_id': self.country_us.id,
        })
        target_func = 'odoo.addons.phone_validation.tools.phone_validation.phone_format'
        with patch(target_func, return_value='+12025550177'):
            action = partner.send_sms()
            ctx = action.get('context', {})
            self.assertIn('+12025550177', ctx.get('default_recipient_numbers'))

    def test_send_sms_partner_phone_validation_exception(self):
        """Action falls back gracefully when phone_validation raises UserError."""
        partner = self.env['res.partner'].create({
            'name': 'Validation Exception',
            'phone': '2025550166',
            'country_id': self.country_us.id,
        })
        target_func = 'odoo.addons.phone_validation.tools.phone_validation.phone_format'
        with patch(target_func, side_effect=UserError('Format error')):
            action = partner.send_sms()
            ctx = action.get('context', {})
            self.assertIn('+12025550166', ctx.get('default_recipient_numbers'))

    def test_send_sms_partner_no_phone(self):
        """Partner without phone returns empty recipient list in context."""
        partner = self.env['res.partner'].create({
            'name': 'No Phone Partner',
        })
        action = partner.send_sms()
        self.assertEqual(
            action.get('context', {}).get('default_recipient_numbers'), ''
        )
