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
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):  # pylint: disable=no-wizard-in-models
    """Inherit res.config.settings to provide multi-currency settings for POS."""
    _inherit = ['res.config.settings', 'pos.load.mixin']

    currency_ids = fields.Many2many(
        'res.currency',
        string="Currencies",
        help="The list of currencies supported by this POS configuration.",
    )
    enable_currency = fields.Boolean(
        string="Enable Multi-Currency",
        default=False,
        help="Enable multi-currency support in the POS.",
    )

    @api.model
    def get_values(self):
        """Load multi-currency configuration values from pos.config into settings.

        :return: Dictionary of configuration parameter values.
        :rtype: dict
        """
        res = super().get_values()
        pos_config = False
        if hasattr(self, 'pos_config_id') and self.pos_config_id:
            pos_config = self.pos_config_id
        elif self.env.context.get('pos_config_id'):
            pos_config = self.env['pos.config'].browse(self.env.context['pos_config_id'])
        else:
            pos_config = self.env['pos.config'].search([], limit=1)

        if pos_config:
            res.update({
                'enable_currency': pos_config.enable_multicurrency,
                'currency_ids': [(6, 0, pos_config.currency_ids.ids)],
            })
        return res

    def set_values(self):
        """Save multi-currency configuration values from settings into pos.config."""
        res = super().set_values()
        pos_config = False
        if hasattr(self, 'pos_config_id') and self.pos_config_id:
            pos_config = self.pos_config_id
        elif self.env.context.get('pos_config_id'):
            pos_config = self.env['pos.config'].browse(self.env.context['pos_config_id'])
        else:
            pos_config = self.env['pos.config'].search([], limit=1)

        if pos_config:
            pos_config.enable_multicurrency = self.enable_currency
            pos_config.currency_ids = [(6, 0, self.currency_ids.ids)]
        return res

    @api.model
    def _load_pos_data_fields(self, config):
        """Return the list of fields to be loaded into POS.

        :param record config: pos.config record.
        :return: List of field names.
        :rtype: list[str]
        """
        return ['enable_currency', 'currency_ids']
