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

{
    'name': 'Mobile Service Management Pro',
    'version': '19.0.1.0.0',
    'category': 'Industries',
    'summary': 'An extended version of Mobile Service Management with IMEI lookup, '
               'device photo capture, pivot analytics and advanced PDF/XLSX reports.',
    'description': (
        "This app offers more advanced features than Mobile Service Management, "
        "such as device details from IMEI number via ImeiCheck.com API, "
        "customized pivot reports, and image capture for service devices."
    ),
    'author': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['mobile_service_shop'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/mobile_service_views.xml',
        'wizard/mobile_service_report_views.xml',
        'wizard/mobile_parts_report_views.xml',
        'wizard/complaint_type_report_views.xml',
        'views/mobile_pivot_report_views.xml',
        'report/complaint_type_report.xml',
        'report/complaint_type_report_templates.xml',
        'report/mobile_parts_report.xml',
        'report/mobile_parts_report_templates.xml',
        'report/mobile_service_report.xml',
        'report/mobile_service_report_templates.xml',
        'report/mobile_service_ticket_report_templates.xml',
        'views/menuitems.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mobile_service_shop_pro/static/src/js/action_manager.js',
        ],
    },
    'images': ['static/description/banner.jpg'],
    'license': 'OPL-1',
    'price': 99,
    'currency': 'EUR',
    'installable': True,
    'application': False,
    'auto_install': False,
}

