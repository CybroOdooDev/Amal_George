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
class TestSmsHistory(TransactionCase):
    """Test suite for sms.history model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gateway = cls.env.ref('multi_sms_gateway.sms_gateway_twilio')

    def test_create_history_record(self):
        """Verify creation and default values for sms.history."""
        history = self.env['sms.history'].create({
            'sms_gateway_id': self.gateway.id,
            'sms_mobile': '+1234567890',
            'sms_text': 'Test SMS content',
        })
        self.assertTrue(history.id)
        self.assertEqual(history.sms_gateway_id, self.gateway)
        self.assertEqual(history.sms_mobile, '+1234567890')
        self.assertEqual(history.sms_text, 'Test SMS content')
        self.assertEqual(history.company_id, self.env.company)
        self.assertTrue(history.sms_date)

    def test_history_ordering(self):
        """Verify sorting order of sms.history records (sms_date desc, id desc)."""
        history1 = self.env['sms.history'].create({
            'sms_gateway_id': self.gateway.id,
            'sms_mobile': '+1000000001',
            'sms_text': 'First',
        })
        history2 = self.env['sms.history'].create({
            'sms_gateway_id': self.gateway.id,
            'sms_mobile': '+1000000002',
            'sms_text': 'Second',
        })
        records = self.env['sms.history'].search([('id', 'in', [history1.id, history2.id])])
        self.assertEqual(records[0], history2)
        self.assertEqual(records[1], history1)
