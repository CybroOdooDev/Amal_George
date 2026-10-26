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

from odoo import api, models


class MobileServiceTicketTemplate(models.AbstractModel):
    """Extends the base service ticket report with Pro fields:
    real_phone_image, IMEI number, complaint visibility."""
    _inherit = 'report.mobile_service_shop.mobile_service_ticket_template'

    @api.model
    def _get_report_values(self, docids, data):
        """Prepare values for rendering the extended Pro customer service ticket PDF.

        Loads system terms/conditions and constructs values mapping for the QWeb context.
        """
        terms = self.env['terms.conditions'].search([])
        return {
            'date_today': data.get('date_today'),
            'date_request': data.get('date_request'),
            'date_return': data.get('date_return'),
            'sev_id': data.get('sev_id'),
            'imei_no': data.get('imei_no'),
            'technician': data.get('technician'),
            'complaint_types': data.get('complaint_types'),
            'complaint_description': data.get('complaint_description'),
            'mobile_brand': data.get('mobile_brand'),
            'model_name': data.get('model_name'),
            'customer_name': data.get('customer_name'),
            'warranty': data.get('warranty'),
            'real_phone_image': data.get('real_phone_image'),
            'terms': terms,
        }


