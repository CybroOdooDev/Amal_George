# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(odoo@cybrosys.com)
#
#    This program is under the terms of the Odoo Proprietary License v1.0(OPL-1)
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
from odoo import fields, models


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('saferpay', "saferpay")],
        ondelete={'saferpay': 'set default'}
    )
    customer = fields.Char(string='Customer ID', help="Customer ID get from "
                                                      "Signup credential")
    terminal = fields.Char(string="Terminal ID", help="Terminal Id get from "
                                                      "signup credential")
    username = fields.Char(help="Username of Safer-pay")
    password = fields.Char(help="Password of Safer-pay")

    def _get_default_payment_method_codes(self):
        self.ensure_one()
        if self.code != 'saferpay':
            return super()._get_default_payment_method_codes()
        return {'saferpay'}

    def _saferpay_get_api_url(self):
        """Return the API endpoint URL based on the provider mode."""
        self.ensure_one()
        if self.is_live:
            return 'https://www.saferpay.com/api'
        return 'https://test.saferpay.com/api'
