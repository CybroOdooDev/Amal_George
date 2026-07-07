# -*- coding: utf-8 -*-
################################################################################
#
#    Mobile Service Management Pro — Odoo 19
#    Wizard: Complaint Type Report (PDF + XLSX)
#
################################################################################
import datetime
import io
import json
from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError

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


class ComplaintTypeReport(models.TransientModel):
    """Wizard for generating Complaint Type Reports (PDF and XLSX).
    Filters by date range and optionally a specific complaint type.
    """
    _name = 'complaint.type.report'
    _description = 'Complaint Type Report'

    date_start = fields.Date(string="Start Date")
    date_end = fields.Date(
        string="End Date",
        default=fields.Date.today,
        required=True,
    )
    complaint_id = fields.Many2one(
        'mobile.complaint',
        string="Complaint Type",
        help="Filter by complaint type. Leave blank for all.",
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def get_report_data(self):
        if self.date_start and self.date_start > self.date_end:
            raise UserError(_("Start date must be before or equal to end date."))
        return {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_start': str(self.date_start) if self.date_start else False,
                'date_end': str(self.date_end),
                'complaint_type': self.complaint_id.id if self.complaint_id else False,
            },
        }

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def print_pdf_report(self):
        data = self.get_report_data()
        return self.env.ref(
            'mobile_service_shop_pro.action_complaint_type_report'
        ).report_action(self, data=data)

    def print_xlsx_report(self):
        data = self.get_report_data()
        return {
            'type': 'ir.actions.report',
            'data': {
                'model': 'complaint.type.report',
                'options': json.dumps(data, default=json_default),
                'output_format': 'xlsx',
                'report_name': 'Complaint Type Report',
            },
            'report_type': 'service_xlsx',
        }

    def get_xlsx_report(self, data, response):
        """Write the Complaint Type XLSX workbook into the HTTP response stream."""
        form = data['form']
        domain = []
        if form['date_start']:
            domain.append(('write_date', '>=', form['date_start']))
        domain.append(('write_date', '<=', form['date_end']))
        if form['complaint_type']:
            domain.append(('complaint_type_tree', '=', form['complaint_type']))

        complaints = self.env['mobile.complaint.tree'].search(domain)
        if not complaints:
            raise ValidationError(_("No complaint data found for the selected filters."))

        # Build data structures
        complaint_list = []
        for line in self.env['mobile.complaint.description'].search([]):
            complaint_list.append({
                'complaint_type': line.complaint_type_template.complaint_type,
                'description': line.description,
                'print': False,
            })

        complaint_detail = []
        for line in complaints:
            complaint_detail.append({
                'complaint_type': line.complaint_type_tree.complaint_type,
                'description': line.description_tree.description,
                'serv_no': line.complaint_id.name,
                'brand': line.complaint_id.brand_name.brand_name,
                'model': line.complaint_id.model_name.mobile_brand_models,
                'date': str(line.complaint_id.date_request or ''),
                'technician': line.complaint_id.technician_name.name,
            })

        for lst in complaint_list:
            for detail in complaint_detail:
                if (lst['complaint_type'] == detail['complaint_type']
                        and lst['description'] == detail['description']):
                    lst['print'] = True

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Complaint Report')

        fmt_head = workbook.add_format({'align': 'center', 'bold': True, 'font_size': 20, 'border': 1})
        fmt_label = workbook.add_format({'bold': True, 'font_size': 10})
        fmt_col = workbook.add_format({'bold': True, 'font_size': 10, 'border': 1})
        fmt_grp = workbook.add_format({'bold': True, 'font_size': 10, 'border': 1, 'bg_color': '#d9e1f2'})
        fmt_cell = workbook.add_format({'font_size': 10, 'border': 1})

        sheet.merge_range('C2:G3', 'COMPLAINT TYPE REPORT', fmt_head)
        sheet.write('C5', "FROM", fmt_label)
        sheet.write('D5', form.get('date_start', ''), fmt_label)
        sheet.write('F5', "TO", fmt_label)
        sheet.write('G5', form['date_end'], fmt_label)

        headers = ['SERV NO.', 'TECHNICIAN', 'BRAND', 'MODEL', 'DATE REQUEST']
        for col, hdr in enumerate(headers, start=2):
            sheet.write(6, col, hdr, fmt_col)
            sheet.set_column(col, col, 20)

        row = 7
        for item in complaint_list:
            if not item['print']:
                continue
            group_label = f"{item['complaint_type']} — {item['description']}"
            sheet.merge_range(row, 2, row, 6, group_label, fmt_grp)
            row += 1
            for detail in complaint_detail:
                if (item['complaint_type'] == detail['complaint_type']
                        and item['description'] == detail['description']):
                    sheet.write(row, 2, detail['serv_no'] or '', fmt_cell)
                    sheet.write(row, 3, detail['technician'] or '', fmt_cell)
                    sheet.write(row, 4, detail['brand'] or '', fmt_cell)
                    sheet.write(row, 5, detail['model'] or '', fmt_cell)
                    sheet.write(row, 6, detail['date'] or '', fmt_cell)
                    row += 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
