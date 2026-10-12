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
from odoo import _, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_open_address_extractor(self):
        """Open the AI Address Extraction wizard for this contact record."""
        self.ensure_one()
        context = {
            'default_partner_id': self.id,
            'active_id': self.id,
            'active_model': 'res.partner',
        }
        # Prepopulate with existing formatted address if available
        address_parts = [
            self.street,
            self.street2,
            self.city,
            self.state_id.name if self.state_id else False,
            self.zip,
            self.country_id.name if self.country_id else False,
        ]
        non_empty_parts = [part.strip() for part in address_parts if part and part.strip()]
        if non_empty_parts:
            context['default_raw_address'] = ", ".join(non_empty_parts)

        return {
            'name': _('AI Address Extractor'),
            'type': 'ir.actions.act_window',
            'res_model': 'address.extraction.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }
