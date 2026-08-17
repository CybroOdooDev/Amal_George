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

from odoo import api, models, _
from odoo.exceptions import ValidationError


class MobilePartsReport(models.AbstractModel):
    """Abstract model that provides data to the Mobile Parts PDF report template."""
    _name = 'report.mobile_service_shop_pro.mobile_parts_report'
    _description = 'Mobile Parts Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Retrieve and compile parts usage records for the PDF report template.

        Retrieves part template details and individual usage transactions (lines)
        based on date range and optional part filters, formatting them for rendering.
        """
        form = data['form']

        if form.get('date_start'):
            order_lines = self.env['product.order.line'].search([
                ('product_order_id.date_request', '>=', form['date_start']),
                ('product_order_id.date_request', '<=', form['date_end']),
            ])
        else:
            order_lines = self.env['product.order.line'].search([
                ('product_order_id.date_request', '<=', form['date_end']),
            ])

        used_tmpl_ids = {
            line.product_id.product_tmpl_id.id
            for line in order_lines
            if line.product_id.product_tmpl_id
        }

        domain = [('is_a_parts', '=', True)]
        if form.get('parts_id'):
            domain.append(('id', '=', form['parts_id']))
        products = self.env['product.template'].search(domain)
        products = products.filtered(lambda p: p.id in used_tmpl_ids)

        if not products:
            raise ValidationError(_("No parts usage data found for the selected filters."))

        lst = []
        for product in products:
            lst.append({
                'id': product.id,
                'part_brand': product.brand_name.brand_name or '',
                'part_model': product.model_name.mobile_brand_models or '',
                'part_colour': product.model_colour or '',
                'product_name': product.name,
            })

        lst1 = []
        currency_symbol = self.env.user.company_id.currency_id.symbol or ''
        for line in order_lines:
            lst1.append({
                'product_id': line.product_id.product_tmpl_id.id,
                'serv_id': line.product_order_id.name or '',
                'qty': line.qty_invoiced,
                'qty_used': line.product_uom_qty,
                'qty_stock_move': line.qty_stock_move,
                'price': line.part_price,
                'create_date': line.write_date,
                'technician': line.product_order_id.technician_name.name or '',
                'symbol': currency_symbol,
            })

        return {
            'values': lst,
            'used': lst1,
            'start_date': form.get('date_start'),
            'end_date': form.get('date_end'),
        }


