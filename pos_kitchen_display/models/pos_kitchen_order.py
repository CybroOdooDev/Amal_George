# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author:  Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import models, fields, api

class PosKitchenOrder(models.Model):
    """Model to store POS kitchen orders."""
    _name = 'pos.kitchen.order'
    _description = 'POS Kitchen Order'

    name = fields.Char(string='Order Reference', required=True, default='/')
    state = fields.Selection([
        ('draft', 'To Cook'),
        ('progress', 'Cooking'),
        ('ready', 'Ready'),
        ('done', 'Completed'),
    ], string='Status', default='draft', required=True)
    table_name = fields.Char(string='Table')
    shop_name = fields.Char(string='Shop/POS Config Name')
    line_ids = fields.One2many('pos.kitchen.order.line', 'order_id', string='Order Lines')


class PosKitchenOrderLine(models.Model):
    """Model to store POS kitchen order lines/items."""
    _name = 'pos.kitchen.order.line'
    _description = 'POS Kitchen Order Line'

    order_id = fields.Many2one('pos.kitchen.order', string='Order Reference', ondelete='cascade')
    name = fields.Char(string='Product Name', required=True)
    qty = fields.Float(string='Quantity', default=1.0)
    note = fields.Char(string='Note')
    is_completed = fields.Boolean(string='Is Completed', default=False)


class PosOrder(models.Model):
    """Inherit POS Order to automatically create kitchen tickets."""
    _inherit = 'pos.order'

    @api.model_create_multi
    def create(self, vals_list):
        orders = super(PosOrder, self).create(vals_list)
        for order in orders:
            # Only create kitchen orders for restaurant POS configurations with active floors
            if order.config_id.module_pos_restaurant and order.config_id.floor_ids:
                kitchen_order = self.env['pos.kitchen.order'].create({
                    'name': order.name or order.pos_reference,
                    'table_name': order.table_id.display_name or 'Takeaway',
                    'shop_name': order.config_id.name,
                })
                for line in order.lines:
                    self.env['pos.kitchen.order.line'].create({
                        'order_id': kitchen_order.id,
                        'name': line.product_id.display_name,
                        'qty': line.qty,
                        'note': line.customer_note or line.note or '',
                    })
        return orders
