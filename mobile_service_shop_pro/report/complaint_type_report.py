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


class ComplaintTypeReport(models.AbstractModel):
    """Abstract model that provides data to the Complaint Type PDF report template."""
    _name = 'report.mobile_service_shop_pro.complaint_type_report'
    _description = 'Complaint Type Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Retrieve and process complaint records for the PDF report template.

        Groups matching complaints by category/type and description dynamically,
        returning details for rendering in QWeb.
        """
        form = data['form']
        domain = []
        if form.get('date_start'):
            domain.append(('complaint_id.date_request', '>=', form['date_start']))
        domain.append(('complaint_id.date_request', '<=', form['date_end']))
        if form.get('complaint_type'):
            domain.append(('complaint_type_tree', '=', form['complaint_type']))

        complaints_filtered = self.env['mobile.complaint.tree'].search(domain)
        if not complaints_filtered:
            raise ValidationError(_("No complaint data found for the selected filters."))

        lst = []
        seen = set()
        for line in complaints_filtered:
            c_type = line.complaint_type_tree.complaint_type or ''
            desc = line.description_tree.description or ''
            key = (c_type, desc)
            if key not in seen:
                seen.add(key)
                lst.append({
                    'complaint_type': c_type,
                    'description': desc,
                    'print': 1,
                })

        lst1 = []
        for line in complaints_filtered:
            lst1.append({
                'complaint_type': line.complaint_type_tree.complaint_type or '',
                'description': line.description_tree.description or '',
                'serv_no': line.complaint_id.name or '',
                'brand': line.complaint_id.brand_name.brand_name or '',
                'model': line.complaint_id.model_name.mobile_brand_models or '',
                'date': line.complaint_id.date_request,
                'technician': line.complaint_id.technician_name.name or '',
            })

        return {
            'values': lst,
            'complaints': lst1,
            'start_date': form.get('date_start'),
            'end_date': form.get('date_end'),
        }


