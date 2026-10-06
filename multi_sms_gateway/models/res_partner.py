# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import _, models


class ResPartner(models.Model):
    """
    Inheriting res.partner to integrate direct SMS sending capabilities.
    Provides action to launch the Send SMS wizard prefilled with the partner's phone number.
    """
    _inherit = 'res.partner'

    def send_sms(self):
        """
        Action method to open the Send SMS wizard prefilled with partner phone numbers.

        Extracts and normalizes phone numbers for selected partners, locates the default
        SMS gateway configuration, and returns the window action to launch the wizard.

        Returns:
            dict: An ir.actions.act_window action dictionary displaying 'send.sms' in a modal.
        """
        partner_records = self.browse(self.env.context.get('active_ids') or self.ids)
        phone_numbers = []
        for partner in partner_records:
            phone_number = partner.phone if 'phone' in partner._fields else False
            if not phone_number and 'mobile' in partner._fields:
                phone_number = partner.mobile
            if phone_number:
                phone_number = str(phone_number).strip()
                if not phone_number.startswith('+'):
                    country = partner.country_id or self.env.company.country_id
                    if country and country.phone_code:
                        try:
                            from odoo.addons.phone_validation.tools import phone_validation
                            formatted_number = phone_validation.phone_format(
                                phone_number,
                                country.code,
                                country.phone_code,
                                force_format='E164'
                            )
                            if formatted_number:
                                phone_number = formatted_number
                        except Exception:
                            clean_digits = ''.join(char for char in phone_number if char.isdigit())
                            if clean_digits.startswith(str(country.phone_code)):
                                phone_number = f"+{clean_digits}"
                            else:
                                phone_number = f"+{country.phone_code}{clean_digits}"
                phone_numbers.append(phone_number)

        default_gateway_config = self.env['sms.gateway.config'].search([], limit=1)
        return {
            'name': _('Send SMS'),
            'type': 'ir.actions.act_window',
            'res_model': 'send.sms',
            'context': {
                'default_recipient_numbers': ','.join(phone_numbers),
                'default_gateway_config_id': default_gateway_config.id if default_gateway_config else False,
            },
            'view_mode': 'form',
            'target': 'new'
        }
