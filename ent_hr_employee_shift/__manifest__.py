# -*- coding: utf-8 -*-
######################################################################################
#
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#    or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#    ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
########################################################################################
{
    'name': "Enterprise Open HRMS Employee Shift",
    'version': '19.0.1.0.0',
    'category': 'Human Resource',
    'summary': """Easily create, manage, and track employee shift schedules.""",
    'description': """This module is used to track employee shift schedules. We
    can easily create employee shifts and adjust them accordingly.""",
    'author': "Cybrosys Techno Solutions,Open HRMS",
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.openhrms.com",
    'depends': ['hr_payroll', 'resource'],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_shift_schedule_rule.xml',
        'views/hr_employee_views.xml',
        'views/resource_calendar_views.xml',
        'views/hr_generate_shift_views.xml',
    ],
    'demo': [
        'demo/ent_hr_employee_shift_demo.xml',
    ],
    'images': ["static/description/banner.jpg"],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': True,
}