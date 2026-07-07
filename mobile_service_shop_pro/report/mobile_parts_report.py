# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.exceptions import ValidationError


class MobilePartsReport(models.AbstractModel):
    """Abstract model that provides data to the Mobile Parts PDF report template."""
    _name = 'report.mobile_service_shop_pro.mobile_parts_report'
    _description = 'Mobile Parts Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        form = data['form']

        if form.get('date_start'):
            order_lines = self.env['product.order.line'].search([
                ('write_date', '>=', form['date_start']),
                ('write_date', '<=', form['date_end']),
            ])
        else:
            order_lines = self.env['product.order.line'].search([])

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
