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
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestResConfigSettings(TransactionCase):
    """Test multi-currency configuration in res.config.settings."""

    def setUp(self):
        super().setUp()
        self.currency_eur = self.env.ref('base.EUR', raise_if_not_found=False)
        if not self.currency_eur:
            self.currency_eur = self.env['res.currency'].create({
                'name': 'EUR',
                'symbol': '€',
                'rate': 1.1,
                'active': True,
            })
        else:
            self.currency_eur.write({'active': True, 'rate': 1.1})

        self.currency_usd = self.env.ref('base.USD', raise_if_not_found=False)
        if not self.currency_usd:
            self.currency_usd = self.env['res.currency'].create({
                'name': 'USD',
                'symbol': '$',
                'rate': 1.0,
                'active': True,
            })
        else:
            self.currency_usd.write({'active': True, 'rate': 1.0})

        self.pos_config = self.env['pos.config'].create({
            'name': 'Settings Test POS',
            'enable_multicurrency': False,
        })
        self.pos_config.currency_ids = [(6, 0, [])]

    def test_get_values(self):
        """Test get_values loads multicurrency configuration from pos.config."""
        self.pos_config.enable_multicurrency = True
        self.pos_config.currency_ids = [(6, 0, [self.currency_eur.id])]

        settings = self.env['res.config.settings'].with_context(pos_config_id=self.pos_config.id)
        values = settings.get_values()

        self.assertTrue(values.get('enable_currency'))
        self.assertEqual(values.get('currency_ids'), [(6, 0, [self.currency_eur.id])])

    def test_set_values(self):
        """Test set_values saves multicurrency configuration from settings into pos.config."""
        settings = self.env['res.config.settings'].with_context(pos_config_id=self.pos_config.id).create({
            'pos_config_id': self.pos_config.id,
            'enable_currency': True,
            'currency_ids': [(6, 0, [self.currency_eur.id, self.currency_usd.id])],
        })
        settings.set_values()

        self.assertTrue(self.pos_config.enable_multicurrency)
        self.assertIn(self.currency_eur, self.pos_config.currency_ids)
        self.assertIn(self.currency_usd, self.pos_config.currency_ids)

    def test_load_pos_data_fields(self):
        """Test _load_pos_data_fields executes on res.config.settings."""
        settings_model = self.env['res.config.settings']
        fields = settings_model._load_pos_data_fields(self.pos_config)
        self.assertIsInstance(fields, list)
        self.assertIn('enable_currency', fields)
        self.assertIn('currency_ids', fields)
