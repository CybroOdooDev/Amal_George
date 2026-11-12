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
from odoo.tests import TransactionCase


class SaferpayCommon(TransactionCase):
    """Common test setup for Saferpay tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.currency = cls.env.ref('base.EUR', raise_if_not_found=False) or cls.env['res.currency'].search([('active', '=', True)], limit=1)
        cls.partner = cls.env['res.partner'].create({
            'name': 'Saferpay Test Customer',
            'email': 'customer@example.com',
        })

        cls.provider = cls.env['payment.provider'].create({
            'name': 'Saferpay Payment Gateway',
            'code': 'saferpay',
            'is_live': False,
            'customer': '287995',
            'terminal': '17781432',
            'username': 'API_287995_test',
            'password': 'TestPassword123!',
        })

        cls.payment_method = cls.env['payment.method'].search([
            ('code', '=', 'saferpay'),
            ('provider_id', '=', cls.provider.id),
        ], limit=1)

        if not cls.payment_method:
            cls.payment_method = cls.env['payment.method'].create({
                'name': 'Saferpay',
                'code': 'saferpay',
                'provider_id': cls.provider.id,
                'active': True,
            })

