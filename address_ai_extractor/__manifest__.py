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
    'name': 'Google GenAI Address Extraction',
    'version': '20.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Extract and parse full addresses into structured contact fields using Google Gemini AI',
    'description': """
Google GenAI Address Extraction for Odoo 20
============================================
Seamlessly extract unstructured, single-string addresses into individual
Odoo address fields (Street, Street 2, City, State, ZIP, Country) using
Google Gemini AI and the official google-genai Python SDK.

Key Features:
-------------
* Official Google GenAI Python SDK (`google-genai`) integration.
* Secure Gemini API key configuration with real-time connection test.
* Single-field address input with intelligent component parsing.
* Accurate resolution of State and Country against existing Odoo records without creating duplicates.
* Dual workflow: apply extracted address to an existing contact or create a new contact.
* Safeguard protection: prevents accidental overwrite of existing contact details without user consent.
* Handles international and multi-line address formats gracefully.
    """,
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'license': 'LGPL-3',
    'depends': ['base', 'base_setup', 'contacts'],
    'data': [
        'security/ir.access.csv',
        'data/ir_config_parameter_data.xml',
        'views/res_config_settings_views.xml',
        'views/address_extraction_wizard_views.xml',
        'views/res_partner_views.xml',
        'views/address_menus.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
