# -*- coding: utf-8 -*-
################################################################################
#
#    Mobile Service Management Pro — Odoo 19
#    Product order line — auto-filter parts by brand/model
#
################################################################################
from odoo import api, models


class ProductOrderLine(models.Model):
    """Extends product.order.line to auto-populate price/UoM when a part is
    selected, and filter available parts by the service's brand and model.
    """
    _inherit = 'product.order.line'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-fill price and unit of measure; return a domain that restricts
        the product selection to parts matching the service's brand/model."""
        self.ensure_one()
        filter_list = [('is_a_parts', '=', True)]
        if self.product_order_id.brand_name:
            filter_list.append(
                ('brand_name', '=', self.product_order_id.brand_name.id))
        if self.product_order_id.model_name:
            filter_list.append(
                ('model_name', '=', self.product_order_id.model_name.id))

        if self.product_id:
            product_template = self.product_id.product_tmpl_id
            self.price_unit = product_template.list_price
            self.product_uom = product_template.uom_id.name

        return {'domain': {'product_id': filter_list}}
