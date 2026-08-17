# -- coding: utf-8 --
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Technologies(odoo@cybrosys.com)
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the
#    Software or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NON INFRINGEMENT. IN NO EVENT SHALL
#    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,ARISING
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
###############################################################################

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    """Extends res.config.settings with Mobile Service Pro configuration:
    - ImeiCheck.com API key and toggle
    - Show/hide complaints on printed tickets
    """
    _inherit = 'res.config.settings'

    api_key = fields.Char(
        string="ImeiCheck API Key",
        help=(
            "Personal API key from ImeiCheck.com. Contact them via "
            "https://imeicheck.com/contact to register and receive limited "
            "credits for testing."
        ),
        config_parameter="mobile_service_shop_pro.api_key",
    )

    get_api_details = fields.Boolean(
        string="IMEI Device Lookup & Auto-Fill",
        help=(
            "Enable this to allow technicians to auto-fill device brand, model, "
            "and manufacturer by entering an IMEI number and clicking 'Get Details'.\n"
            "Please provide the credentials below to enable this feature."
        ),
        config_parameter="mobile_service_shop_pro.get_api_details",
    )
    show_complain_types = fields.Boolean(
        string="Show Complaints on Ticket",
        help=(
            "When enabled, complaint types and descriptions are printed "
            "on the customer service ticket PDF."
        ),
        config_parameter="mobile_service_shop_pro.show_complain_types",
    )
    mobileapi_key = fields.Char(
        string="MobileAPI.dev API Key",
        help="API Key from MobileAPI.dev to fetch device images.",
        config_parameter="mobile_service_shop_pro.mobileapi_key",
    )
    fetch_device_images = fields.Boolean(
        string="Fetch Device Images",
        help=(
            "Enable this to automatically fetch device images from MobileAPI.dev "
            "when lookup is executed.\n"
            "Requires a valid MobileAPI.dev API key."
        ),
        config_parameter="mobile_service_shop_pro.fetch_device_images",
    )

    def action_imeicheck_login(self):
        """Redirect to ImeiCheck.com login dashboard."""
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://imeicheck.com/dashboard/auth/login',
            'target': 'new',
        }

    def action_mobileapi_login(self):
        """Redirect to MobileAPI.dev login page."""
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://mobileapi.dev/signin/',
            'target': 'new',
        }

    @api.onchange('get_api_details')
    def _onchange_get_api_details(self):
        """Clear dependent fields when get_api_details is disabled."""
        if not self.get_api_details:
            self.api_key = False
            self.fetch_device_images = False
            self.mobileapi_key = False

    @api.onchange('fetch_device_images')
    def _onchange_fetch_device_images(self):
        """Clear dependent mobileapi_key when fetch_device_images is disabled."""
        if not self.fetch_device_images:
            self.mobileapi_key = False

    @api.model
    def default_get(self, fields):
        """Load settings values, clearing API key fields in memory if disabled."""
        res = super().default_get(fields)
        if not res.get('get_api_details'):
            res.update({
                'api_key': False,
                'fetch_device_images': False,
                'mobileapi_key': False,
            })
        elif not res.get('fetch_device_images'):
            res.update({
                'mobileapi_key': False,
            })
        return res

    def set_values(self):
        """Save settings values, clearing API keys from DB parameters if toggles are off."""
        if not self.get_api_details:
            self.api_key = False
            self.fetch_device_images = False
            self.mobileapi_key = False
        elif not self.fetch_device_images:
            self.mobileapi_key = False
        super().set_values()







