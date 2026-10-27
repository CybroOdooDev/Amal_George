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
from odoo.tests import TransactionCase, tagged


@tagged('post_install', 'at_install')
class TestSmsGateway(TransactionCase):
    """Test suite for sms.gateway model."""

    def test_default_gateways_exist(self):
        """Verify default gateway records created from data file."""
        twilio_gateway = self.env.ref(
            'multi_sms_gateway.sms_gateway_twilio', raise_if_not_found=False
        )
        vonage_gateway = self.env.ref(
            'multi_sms_gateway.sms_gateway_vonage', raise_if_not_found=False
        )
        telesign_gateway = self.env.ref(
            'multi_sms_gateway.sms_gateway_telesign', raise_if_not_found=False
        )

        self.assertTrue(twilio_gateway, "Twilio gateway record should exist.")
        self.assertEqual(twilio_gateway.name, 'Twilio')
        self.assertTrue(vonage_gateway, "Vonage gateway record should exist.")
        self.assertEqual(vonage_gateway.name, 'Vonage')
        self.assertTrue(telesign_gateway, "TeleSign gateway record should exist.")
        self.assertEqual(telesign_gateway.name, 'TeleSign')

    def test_create_custom_gateway(self):
        """Verify custom gateway provider creation."""
        custom_gateway = self.env['sms.gateway'].create({
            'name': 'CustomProvider',
        })
        self.assertEqual(custom_gateway.name, 'CustomProvider')
