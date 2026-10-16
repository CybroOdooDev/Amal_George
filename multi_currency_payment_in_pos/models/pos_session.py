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
from odoo import api, models


class PosSession(models.Model):
    """Inherit pos.session to include configuration models in POS data loading."""
    _inherit = 'pos.session'
    _description = 'Point of Sale Session'

    @api.model
    def _load_pos_data_models(self, config_id):
        """Add models to be loaded into the POS session cache.

        :param int or record config_id: POS configuration record or ID.
        :return: List of model names to load.
        :rtype: list[str]
        """
        data = super()._load_pos_data_models(config_id)
        if 'res.config.settings' not in data:
            data.append('res.config.settings')
        return data
