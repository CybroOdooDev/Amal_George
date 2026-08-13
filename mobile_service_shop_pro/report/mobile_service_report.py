# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author:Vishnuraj P (odoo@cybrosys.com)
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

from odoo import api, models, _
from odoo.exceptions import ValidationError


class MobileServiceReport(models.AbstractModel):
    """Abstract model that provides data to the Mobile Service PDF report template."""
    _name = 'report.mobile_service_shop_pro.mobile_service_report'
    _description = 'Mobile Service Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Retrieve and process service records for the PDF report template.

        Applies filters such as date, status, and technician to find matching
        service requests and formats their details for QWeb rendering.
        """
        form = data['form']
        domain = [('date_request', '<=', form['date_end'])]
        if form.get('date_start'):
            domain.append(('date_request', '>=', form['date_start']))
        if form.get('service_status'):
            domain.append(('service_state', '=', form['service_status']))
        if form.get('technician_id'):
            domain.append(('technician_name', '=', form['technician_id']))

        service_ids = self.env['mobile.service'].search(domain)
        if not service_ids:
            raise ValidationError(_("No records found for the selected filters."))

        values = []
        for svc in service_ids:
            brand = svc.brand_name.brand_name or ''
            model = svc.model_name.mobile_brand_models or ''
            product_name = f"{brand} ({model})" if brand or model else ''
            state_label = dict(svc._fields['service_state'].selection).get(svc.service_state, '')
            values.append({
                'code': svc.name,
                'customer_name': svc.person_name.name or '',
                'product_name': product_name,
                'date_assign': svc.date_request,
                'date_return': svc.return_date,
                'technician': svc.technician_name.name or '',
                'status': state_label,
            })

        return {
            'values': values,
            'start_date': form.get('date_start'),
            'end_date': form.get('date_end'),
        }


