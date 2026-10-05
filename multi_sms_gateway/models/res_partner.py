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
from odoo import models


class ResPartner(models.Model):
    """
    Inheriting model 'res.partner' to add the function to send SMS.
    Methods:
        send_sms():
            Opens the Send SMS wizard.
    """
    _inherit = 'res.partner'

    def send_sms(self):
        """
        Function to open Send SMS wizard.
        Returns:
            dict: the action window of 'send.sms'.
        """
        partners = self.browse(self.env.context.get('active_ids') or self.ids)
        numbers = []
        for partner in partners:
            num = partner.phone
            if num:
                num = str(num).strip()
                if not num.startswith('+'):
                    country = partner.country_id or self.env.company.country_id
                    if country and country.phone_code:
                        try:
                            from odoo.addons.phone_validation.tools import phone_validation
                            formatted = phone_validation.phone_format(
                                num, country.code, country.phone_code, force_format='E164'
                            )
                            if formatted:
                                num = formatted
                        except Exception:
                            clean_digits = ''.join(c for c in num if c.isdigit())
                            if clean_digits.startswith(str(country.phone_code)):
                                num = f"+{clean_digits}"
                            else:
                                num = f"+{country.phone_code}{clean_digits}"
                numbers.append(num)

        default_gateway = self.env['sms.gateway.config'].search([], limit=1)
        return {
            'name': 'Send SMS',
            'type': 'ir.actions.act_window',
            'res_model': 'send.sms',
            'context': {
                'default_sms_to': ','.join(numbers),
                'default_sms_id': default_gateway.id if default_gateway else False,
            },
            'view_mode': 'form',
            'target': 'new'
        }
