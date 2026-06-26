# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Yadhu Shankar E (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import requests
from odoo import api, fields, models
from exa_py import Exa



class ResConfigSettings(models.TransientModel):
    """Add field to configuration settings"""
    _inherit = 'res.config.settings'

    google_search = fields.Boolean(
        string='Allow the users to synchronize the google search',
        config_parameter='google_search_in_odoo.google_search',
        help="For synchronizing the google search")
    ser_client_api = fields.Char(
        "API Key",
        config_parameter='google_search_in_odoo.ser_client_api',
        help="Google search api key")

    @api.model
    def google_search_config(self, input_data):
        """Create function to get google custom search api response"""
        google_search = self.env['ir.config_parameter'].sudo().get_param(
            'google_search_in_odoo.google_search')
        if not google_search:
            return {
                'error': 'Please enable Google Search.'
            }
        else:
            api_key = self.env['ir.config_parameter'].sudo().get_param(
                'google_search_in_odoo.ser_client_api')
            if not api_key:
                return {
                    'error': 'Please provide API key.'
                }

        try:
            exa = Exa(api_key)
            response = exa.search(
                input_data,
                num_results=10,
                type="auto",
                contents={"highlights": True}
            )

            items = []
            if response and response.results:
                for result in response.results:
                    snippet = ""
                    if result.highlights:
                        snippet = " ... ".join(result.highlights)
                    elif result.summary:
                        snippet = result.summary
                    elif result.text:
                        snippet = result.text[:300] + "..." if len(result.text) > 300 else result.text

                    items.append({
                        'title': result.title or '',
                        'link': result.url or '',
                        'snippet': snippet
                    })
            return items
        except Exception as e:
            return {
                'error': f"Exa Search Error: {str(e)}"
            }
