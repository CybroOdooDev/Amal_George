# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author:Vishnuraj P (odoo@cybrosys.com)
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


