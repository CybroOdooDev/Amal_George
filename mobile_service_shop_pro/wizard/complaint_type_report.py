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

    date_start = fields.Date(
        string="Start Date",
        help="Start date for filtering the complaint type records.")
    date_end = fields.Date(
        string="End Date",
        default=fields.Date.today,
        required=True,
        help="End date for filtering the complaint type records.",
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
        """Prepare the parameters dictionary representing this wizard's filter settings.

        Validates the date range before returning the form data structure.
        """
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

    def _check_data_exists(self):
        """Pre-validate the database to ensure that matching complaint data exists.

        Raises ValidationError if no complaint tree records match the selected date range
        and type filters, preventing printing empty documents.
        """
        self.get_report_data()
        domain = []
        if self.date_start:
            domain.append(('complaint_id.date_request', '>=', self.date_start))
        domain.append(('complaint_id.date_request', '<=', self.date_end))
        if self.complaint_id:
            domain.append(('complaint_type_tree', '=', self.complaint_id.id))
        if not self.env['mobile.complaint.tree'].search(domain):
            raise ValidationError(_("No complaint data found for the selected filters."))

    def print_pdf_report(self):
        """Action that validates input and returns the PDF report printout action."""
        self._check_data_exists()
        data = self.get_report_data()
        return self.env.ref(
            'mobile_service_shop_pro.action_complaint_type_report'
        ).report_action(self, data=data)

    def print_xlsx_report(self):
        """Action that validates input and triggers the custom XLSX report download."""
        self._check_data_exists()
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
        if form.get('date_start'):
            domain.append(('complaint_id.date_request', '>=', form.get('date_start')))
        if form.get('date_end'):
            domain.append(('complaint_id.date_request', '<=', form.get('date_end')))
        if form.get('complaint_type'):
            domain.append(('complaint_type_tree', '=', form.get('complaint_type')))

        complaints = self.env['mobile.complaint.tree'].search(domain)
        if not complaints:
            raise ValidationError(_("No complaint data found for the selected filters."))

        # Build data structures
        complaint_list = []
        seen = set()
        for line in complaints:
            c_type = line.complaint_type_tree.complaint_type or ''
            desc = line.description_tree.description or ''
            key = (c_type, desc)
            if key not in seen:
                seen.add(key)
                complaint_list.append({
                    'complaint_type': c_type,
                    'description': desc,
                    'print': True,
                })

        complaint_detail = []
        for line in complaints:
            complaint_detail.append({
                'complaint_type': line.complaint_type_tree.complaint_type or '',
                'description': line.description_tree.description or '',
                'serv_no': line.complaint_id.name or '',
                'brand': line.complaint_id.brand_name.brand_name or '',
                'model': line.complaint_id.model_name.mobile_brand_models or '',
                'date': str(line.complaint_id.date_request or ''),
                'technician': line.complaint_id.technician_name.name or '',
            })

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


