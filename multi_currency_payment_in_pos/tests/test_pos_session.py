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


@tagged('post_install', 'at_install')
class TestPosSession(TransactionCase):
    """Test model loading parameters on pos.session."""

    def setUp(self):
        super().setUp()
        self.pos_config = self.env['pos.config'].create({
            'name': 'POS Session Test Config',
            'payment_method_ids': [(6, 0, [])],
        })
        self.pos_session_model = self.env['pos.session']

    def test_load_pos_data_models_includes_res_config_settings(self):
        """Test _load_pos_data_models includes res.config.settings and does not duplicate."""
        models = self.pos_session_model._load_pos_data_models(self.pos_config.id)
        self.assertIn('res.config.settings', models)
        self.assertEqual(models.count('res.config.settings'), 1)
