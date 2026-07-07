# -*- coding: utf-8 -*-
################################################################################
#
#    Mobile Service Management Pro — Odoo 19
#    Wizard: Mobile Service Report (PDF + XLSX)
#
################################################################################
import datetime
import io
import json
from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError

# Odoo 17+ moved json_default; graceful fallback
try:
    from odoo.tools.json import json_default
except ImportError:
    def json_default(obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return str(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class MobileServiceReport(models.TransientModel):
    """Wizard for generating Mobile Service Reports (PDF and XLSX).
    Filters by date range, service status, and/or technician.
    """
    _name = 'mobile.service.report'
    _description = 'Mobile Service Report'

    date_start = fields.Date(string="Start Date", help="Filter from this date.")
    date_end = fields.Date(
        string="End Date",
        default=fields.Date.today,
        required=True,
        help="Filter up to and including this date.",
    )
    status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('assigned', 'Assigned'),
            ('completed', 'Completed'),
            ('returned', 'Returned'),
            ('not_solved', 'Not Solved'),
        ],
        string='Service Status',
        default='draft',
    )
    technician_id = fields.Many2one(
        'res.users', string="Technician",
        help="Filter by technician. Leave blank for all.",
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_domain(self):
        """Return an ORM domain based on wizard filter fields."""
        domain = [('date_request', '<=', str(self.date_end))]
        if self.date_start:
            if self.date_start > self.date_end:
                raise UserError(_("Start date must be before or equal to end date."))
            domain.append(('date_request', '>=', str(self.date_start)))
        if self.status:
            domain.append(('service_state', '=', self.status))
        if self.technician_id:
            domain.append(('technician_name', '=', self.technician_id.id))
        return domain

    def get_report_data(self):
        """Return the data dict shared by PDF and XLSX renderers."""
        return {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_start': str(self.date_start) if self.date_start else False,
                'date_end': str(self.date_end),
                'service_status': self.status,
                'technician_id': self.technician_id.id if self.technician_id else False,
                'technician': self.technician_id.name if self.technician_id else False,
            },
        }

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def print_pdf_report(self):
        """Render the Mobile Service PDF report."""
        data = self.get_report_data()
        return self.env.ref(
            'mobile_service_shop_pro.action_mobile_service_report'
        ).report_action(self, data=data)

    def print_xlsx_report(self):
        """Trigger the XLSX download via the custom controller."""
        data = self.get_report_data()
        return {
            'type': 'ir.actions.report',
            'data': {
                'model': 'mobile.service.report',
                'options': json.dumps(data, default=json_default),
                'output_format': 'xlsx',
                'report_name': 'Mobile Service Report',
            },
            'report_type': 'service_xlsx',
        }

    def get_xlsx_report(self, data, response):
        """Write the XLSX workbook into the HTTP response stream."""
        domain = []
        form = data['form']
        if form['date_start']:
            domain.append(('date_request', '>=', form['date_start']))
        domain.append(('date_request', '<=', form['date_end']))
        if form.get('service_status'):
            domain.append(('service_state', '=', form['service_status']))
        if form.get('technician_id'):
            domain.append(('technician_name', '=', form['technician_id']))

        service_ids = self.env['mobile.service'].search(domain)
        if not service_ids:
            raise ValidationError(_("No records found for the selected filters."))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Service Report')

        fmt_head = workbook.add_format({'align': 'center', 'bold': True, 'font_size': 20, 'border': 1})
        fmt_label = workbook.add_format({'bold': True, 'font_size': 10})
        fmt_col = workbook.add_format({'bold': True, 'font_size': 10, 'border': 1})
        fmt_cell = workbook.add_format({'font_size': 10, 'border': 1})

        sheet.merge_range('C2:H3', 'SERVICE REQUEST REPORT', fmt_head)
        sheet.write('C5', "FROM", fmt_label)
        sheet.write('D5', form.get('date_start', ''), fmt_label)
        sheet.write('F5', "TO", fmt_label)
        sheet.write('G5', form['date_end'], fmt_label)

        headers = ['SERV NO.', 'CUSTOMER', 'PRODUCT', 'REQ DATE', 'RET DATE', 'STATE']
        for col, hdr in enumerate(headers, start=2):
            sheet.write(6, col, hdr, fmt_col)
            sheet.set_column(col, col, 18)

        for row, svc in enumerate(service_ids, start=7):
            brand = svc.brand_name.brand_name or ''
            model = svc.model_name.mobile_brand_models or ''
            product_name = f"{brand} ({model})" if brand or model else ''
            state_label = dict(svc._fields['service_state'].selection).get(svc.service_state, '')
            row_data = [
                svc.name,
                svc.person_name.name or '',
                product_name,
                str(svc.date_request or ''),
                str(svc.return_date or ''),
                state_label,
            ]
            for col, val in enumerate(row_data, start=2):
                sheet.write(row, col, val, fmt_cell)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
