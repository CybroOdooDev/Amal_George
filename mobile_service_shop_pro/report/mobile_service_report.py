# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.exceptions import ValidationError


class MobileServiceReport(models.AbstractModel):
    """Abstract model that provides data to the Mobile Service PDF report template."""
    _name = 'report.mobile_service_shop_pro.mobile_service_report'
    _description = 'Mobile Service Report'

    @api.model
    def _get_report_values(self, docids, data=None):
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
