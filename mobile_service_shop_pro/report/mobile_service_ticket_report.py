# -*- coding: utf-8 -*-
from odoo import api, models


class MobileServiceTicketTemplate(models.AbstractModel):
    """Extends the base service ticket report with Pro fields:
    real_phone_image, IMEI number, complaint visibility."""
    _inherit = 'report.mobile_service_shop.mobile_service_ticket_template'

    @api.model
    def _get_report_values(self, docids, data):
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
