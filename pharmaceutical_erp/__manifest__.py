# -*- coding: utf-8 -*-
{
    'name': 'Pharmaceutical ERP',
    'version': '19.0.1.0.0',
    'summary': 'GMP-compliant pharmaceutical manufacturing — core base setup',
    'description': """
        Core base module for Pharmaceutical Manufacturing ERP.
        Extends Purchase, Inventory, Quality, and Manufacturing with
        pharma-specific master data, lot control, and AVL management.
    """,
    'author': 'Your Company',
    'website': '',
    'category': 'Manufacturing',
    'sequence': 50,
    'license': 'LGPL-3',
    'application': True,
    'installable': True,
    'auto_install': False,

    'depends': [
        'mrp',
        'purchase',
        'stock',
        'quality_control',
        'account',
        'hr',
        'portal',
    ],

    'data': [
        # Security (always first)
        'security/pharma_groups.xml',
        'security/ir.model.access.csv',

        # Sequence data
        'data/pharma_sequences.xml',
        'data/mail_template_data.xml',

        # Views — Master Data
        'views/product_template_views.xml',
        'views/pharma_avl_views.xml',
        'views/pharma_qc_spec_views.xml',
        'views/pharma_qc_test_order_views.xml',
        'views/pharma_oos_investigation_views.xml',
        'views/mrp_bom_views.xml',

        # Views — Inventory / Lots
        'views/stock_lot_views.xml',

        # Views — Purchase
        'views/purchase_order_views.xml',

        # Views — Settings
        'views/res_config_settings_views.xml',
        'views/pharma_vendor_qualification_views.xml',
        'views/pharma_questionnaire_views.xml',
        'views/pharma_portal_templates.xml',

        # Views — Menu (always last)
        'views/pharma_menus.xml',
    ],

    'images': ['static/description/icon.png'],
}
