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

class RestaurantBooking(models.Model):
    _name = 'restaurant.booking'
    _description = 'Restaurant Table Booking'
    _inherit = ['pos.load.mixin']

    name = fields.Char(string='Booking ID', required=True, copy=False, readonly=True, default=lambda self: '/')
    partner_id = fields.Many2one('res.partner', string='Customer Name', required=True)
    phone = fields.Char(string='Phone Number')
    booking_date = fields.Datetime(string='Booking Date & Time', required=True)
    table_id = fields.Many2one('restaurant.table', string='Table')
    guests = fields.Integer(string='Number of Guests', default=2)
    booking_line_ids = fields.One2many('restaurant.booking.line', 'booking_id', string='Booking Lines')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], string='Stage', default='pending', required=True)
    config_id = fields.Many2one('pos.config', string='POS Config')
    shop_name = fields.Char(string='Shop Name', related='config_id.name', store=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('restaurant.booking') or '/'
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        return True

    @api.model
    def _load_pos_data_domain(self, data, config):
        return []

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'partner_id', 'phone', 'booking_date', 'table_id', 'guests', 'booking_line_ids', 'state', 'config_id', 'shop_name']


class RestaurantBookingLine(models.Model):
    _name = 'restaurant.booking.line'
    _description = 'Restaurant Table Booking Line'
    _inherit = ['pos.load.mixin']

    booking_id = fields.Many2one('restaurant.booking', string='Booking Reference', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    qty = fields.Float(string='Quantity', default=1.0, required=True)
    display_name = fields.Char(compute='_compute_display_name')

    @api.depends('product_id', 'qty')
    def _compute_display_name(self):
        for line in self:
            qty_str = int(line.qty) if line.qty.is_integer() else line.qty
            line.display_name = f"{qty_str}x {line.product_id.name}" if line.product_id else f"{qty_str}x Product"


    @api.model
    def _load_pos_data_domain(self, data, config):
        return []

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'booking_id', 'product_id', 'qty']


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config):
        data = super()._load_pos_data_models(config)
        if config.module_pos_restaurant:
            data.extend(['restaurant.booking', 'restaurant.booking.line'])
        return data

