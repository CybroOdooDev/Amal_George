# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.exceptions import ValidationError


class ComplaintTypeReport(models.AbstractModel):
    """Abstract model that provides data to the Complaint Type PDF report template."""
    _name = 'report.mobile_service_shop_pro.complaint_type_report'
    _description = 'Complaint Type Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        form = data['form']
        domain = []
        if form.get('date_start'):
            domain.append(('write_date', '>=', form['date_start']))
        domain.append(('write_date', '<=', form['date_end']))
        if form.get('complaint_type'):
            domain.append(('complaint_type_tree', '=', form['complaint_type']))

        complaints_filtered = self.env['mobile.complaint.tree'].search(domain)
        if not complaints_filtered:
            raise ValidationError(_("No complaint data found for the selected filters."))

        lst = []
        for line in self.env['mobile.complaint.description'].search([]):
            lst.append({
                'complaint_type': line.complaint_type_template.complaint_type,
                'description': line.description,
                'print': 0,
            })

        lst1 = []
        for line in complaints_filtered:
            lst1.append({
                'complaint_type': line.complaint_type_tree.complaint_type,
                'description': line.description_tree.description,
                'serv_no': line.complaint_id.name,
                'brand': line.complaint_id.brand_name.brand_name or '',
                'model': line.complaint_id.model_name.mobile_brand_models or '',
                'date': line.complaint_id.date_request,
                'technician': line.complaint_id.technician_name.name or '',
            })

        for lst_obj in lst:
            for lst1_obj in lst1:
                if (lst_obj['complaint_type'] == lst1_obj['complaint_type']
                        and lst_obj['description'] == lst1_obj['description']):
                    lst_obj['print'] = 1

        return {
            'values': lst,
            'complaints': lst1,
            'start_date': form.get('date_start'),
            'end_date': form.get('date_end'),
        }
