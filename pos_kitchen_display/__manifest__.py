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
{
    'name': 'POS Kitchen Display',
    'version': '19.0.1.0.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Kitchen Screen Display for Point of Sale',
    'description': """
POS Kitchen Screen
==================
This module provides a kitchen screen/display interface for Point of Sale orders, supporting restaurant workflows.
    """,
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
        'pos_restaurant',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_kitchen_screen_views.xml',
        'views/restaurant_booking_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pos_kitchen_display/static/src/components/kitchen_display/kitchen_display.js',
            'pos_kitchen_display/static/src/components/kitchen_display/kitchen_display.xml',
            'pos_kitchen_display/static/src/components/kitchen_display/kitchen_display.scss',
            'pos_kitchen_display/static/src/components/booking_display/booking_display.js',
            'pos_kitchen_display/static/src/components/booking_display/booking_display.xml',
            'pos_kitchen_display/static/src/components/booking_display/booking_display.scss',
        ],
        'point_of_sale._assets_pos': [
            'pos_kitchen_display/static/src/pos/**/*',
        ],
    },


    'installable': True,
    'application': True,
    'auto_install': False,
}