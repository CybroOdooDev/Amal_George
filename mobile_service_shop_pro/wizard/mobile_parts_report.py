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


class MobilePartsReport(models.TransientModel):
    """Wizard for generating Mobile Parts Usage Reports (PDF and XLSX).
    Filters by date range and optionally a specific part.
    """
    _name = 'mobile.parts.report'
    _description = 'Mobile Parts Report'

    date_start = fields.Date(
        string="Start Date",
        help="Start date for filtering the parts usage records.")
    date_end = fields.Date(
        string="End Date",
        default=fields.Date.today,
        required=True,
        help="End date for filtering the parts usage records.",
    )
    parts_id = fields.Many2one(
        'product.product',
        string="Part",
        domain=[('is_a_parts', '=', True)],
        help="Filter by a specific part. Leave blank for all parts.",
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _validate_dates(self):
        """Validate start date is before or equal to end date, raising UserError if invalid."""
        if self.date_start and self.date_start > self.date_end:
            raise UserError(_("Start date must be before or equal to end date."))

    def _build_form_data(self):
        """Generate form parameters dictionary for report actions after date validation."""
        self._validate_dates()
        return {
            'date_start': str(self.date_start) if self.date_start else False,
            'date_end': str(self.date_end),
            'parts_id': self.parts_id.product_tmpl_id.id if self.parts_id else False,
        }

    def _check_data_exists(self):
        """Pre-validate the database to ensure that matching parts usage data exists.

        Raises ValidationError if no parts were used or match the selected date range
        and parts template filters, preventing printing empty documents.
        """
        self._validate_dates()
        if self.date_start:
            order_lines = self.env['product.order.line'].search([
                ('product_order_id.date_request', '>=', self.date_start),
                ('product_order_id.date_request', '<=', self.date_end),
            ])
        else:
            order_lines = self.env['product.order.line'].search([
                ('product_order_id.date_request', '<=', self.date_end),
            ])

        used_tmpl_ids = {
            line.product_id.product_tmpl_id.id
            for line in order_lines
            if line.product_id.product_tmpl_id
        }

        domain = [('is_a_parts', '=', True)]
        if self.parts_id:
            domain.append(('id', '=', self.parts_id.product_tmpl_id.id))
        products = self.env['product.template'].search(domain)
        products = products.filtered(lambda p: p.id in used_tmpl_ids)

        if not products:
            raise ValidationError(_("No parts usage data found for the selected filters."))

    def print_pdf_report(self):
        """Action that validates input and returns the PDF report printout action."""
        self._check_data_exists()
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': self._build_form_data(),
        }
        return self.env.ref(
            'mobile_service_shop_pro.action_mobile_parts_report'
        ).report_action(self, data=data)

    def print_xlsx_report(self):
        """Action that validates input and triggers the custom XLSX report download."""
        self._check_data_exists()
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': self._build_form_data(),
        }
        return {
            'type': 'ir.actions.report',
            'data': {
                'model': 'mobile.parts.report',
                'options': json.dumps(data, default=json_default),
                'output_format': 'xlsx',
                'report_name': 'Mobile Parts Report',
            },
            'report_type': 'service_xlsx',
        }

    def get_xlsx_report(self, data, response):
        """Write the Parts Usage XLSX workbook into the HTTP response stream."""
        form = data['form']
        if form.get('date_start'):
            order_lines = self.env['product.order.line'].search([
                ('product_order_id.date_request', '>=', form.get('date_start')),
                ('product_order_id.date_request', '<=', form.get('date_end')),
            ])
        else:
            order_lines = self.env['product.order.line'].search([
                ('product_order_id.date_request', '<=', form.get('date_end')),
            ])

        used_tmpl_ids = {
            line.product_id.product_tmpl_id.id
            for line in order_lines
            if line.product_id.product_tmpl_id
        }

        domain = [('is_a_parts', '=', True)]
        if form['parts_id']:
            domain.append(('id', '=', form['parts_id']))
        products = self.env['product.template'].search(domain)
        products = products.filtered(lambda p: p.id in used_tmpl_ids)

        if not products:
            raise ValidationError(_("No parts usage data found for the selected filters."))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Parts Report')

        fmt_head = workbook.add_format({'align': 'center', 'bold': True, 'font_size': 20, 'border': 1})
        fmt_label = workbook.add_format({'bold': True, 'font_size': 10})
        fmt_col = workbook.add_format({'bold': True, 'font_size': 10, 'border': 1})
        fmt_part = workbook.add_format({'bold': True, 'font_size': 10, 'border': 1, 'bg_color': '#d9e1f2'})
        fmt_cell = workbook.add_format({'font_size': 10, 'border': 1})

        sheet.merge_range('C2:I3', 'PARTS USAGE REPORT', fmt_head)
        sheet.write('C5', "FROM", fmt_label)
        sheet.write('D5', form.get('date_start', ''), fmt_label)
        sheet.write('F5', "TO", fmt_label)
        sheet.write('G5', form['date_end'], fmt_label)

        headers = ['SERV NO.', 'TECHNICIAN', 'USED DATE', 'QTY USED', 'QTY INVOICED', 'QTY STOCK MOVE', 'PRICE']
        for col, hdr in enumerate(headers, start=2):
            sheet.write(6, col, hdr, fmt_col)
            sheet.set_column(col, col, 18)

        currency_symbol = self.env.user.company_id.currency_id.symbol or ''
        row = 7
        for product in products:
            name_parts = [
                product.name,
                product.brand_name.brand_name or '',
                product.model_name.mobile_brand_models or '',
                product.model_colour or '',
            ]
            display_name = ' | '.join(p for p in name_parts if p)
            sheet.merge_range(row, 2, row, 8, display_name, fmt_part)
            row += 1
            for line in order_lines:
                if line.product_id.product_tmpl_id.id == product.id:
                    sheet.write(row, 2, line.product_order_id.name or '', fmt_cell)
                    sheet.write(row, 3, line.product_order_id.technician_name.name or '', fmt_cell)
                    sheet.write(row, 4, str(line.write_date or ''), fmt_cell)
                    sheet.write(row, 5, line.product_uom_qty, fmt_cell)
                    sheet.write(row, 6, line.qty_invoiced, fmt_cell)
                    sheet.write(row, 7, line.qty_stock_move, fmt_cell)
                    sheet.write(row, 8, f"{line.part_price}{currency_symbol}", fmt_cell)
                    row += 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()


