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
{
    'name': "Saferpay Payment Gateway Integration",
    'version': '20.0.1.0.0',
    'category': 'eCommerce',
    'summary': 'Saferpay Payment Gateway',
    'description': """Saferpay Payment Gateway, related to Payment Gateway
    integration in an eCommerce system""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['account', 'website_sale'],
    'data': [
        'data/payment_provider_data.xml',
        'data/payment_method_data.xml',
        'views/saferpay_payment_templates.xml',
        'views/payment_provider_view.xml',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'images': ['static/description/banner.jpg'],
    'license': 'OPL-1',
    'price': 99,
    'currency': 'EUR',
    'installable': True,
    'auto_install': False,
    'application': False,
}
