# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Yadhu Shankar E (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import api, fields, models


class PosPayment(models.Model):
    """Adding currency symbol and amount."""
    _inherit = 'pos.payment'

    payment_currency = fields.Char(
        string='Payment Currency',
        compute='_compute_payment_currency_fields',
        store=True,
        readonly=False,
        help='Currency in POS settings.'
    )
    currency_amount = fields.Float(
        string='Currency Amount',
        compute='_compute_payment_currency_fields',
        store=True,
        readonly=False,
        help='Currency amount settings.'
    )

    @api.depends('amount', 'currency_id', 'pos_order_id.currency_id')
    def _compute_payment_currency_fields(self):
        for payment in self:
            if not payment.payment_currency:
                currency = payment.currency_id or (payment.pos_order_id.currency_id if payment.pos_order_id else False)
                payment.payment_currency = currency.name if currency else ''
            if not payment.currency_amount and payment.amount:
                payment.currency_amount = payment.amount

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('payment_currency'):
                order_id = vals.get('pos_order_id')
                if order_id:
                    order = self.env['pos.order'].browse(order_id)
                    vals['payment_currency'] = order.currency_id.name or ''
            if not vals.get('currency_amount') and vals.get('amount'):
                vals['currency_amount'] = vals['amount']
        return super().create(vals_list)
