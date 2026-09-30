# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#############################################################################
{
    'name': 'Project Dashboard',
    'version': '20.0.1.0.0',
    'category': 'Extra Tools',
    'summary': """Get a Detailed View for Project.""",
    'description': """In this dashboard user can get the Detailed Information 
     about Project, Task, Employee, Hours recorded, Total Margin and Total 
     Sale Orders.""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': ['sale_management', 'project', 'sale_timesheet'],
    'data': ['views/dashboard_views.xml'],
    'assets': {
        'web.assets_backend': [
            'project_dashboard_odoo/static/src/js/dashboard.js',
            'project_dashboard_odoo/static/src/css/dashboard.css',
            'project_dashboard_odoo/static/src/xml/dashboard_templates.xml',
            'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.4/Chart.js'
        ]},
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}

