# -*- coding: utf-8 -*-
{
    'name': 'Lamèss Accounting',
    'version': '19.0.1.0.12',
    'category': 'Lamèss/Accounting',
    'summary': 'Payout, withholding and accounting integration',
    'description': """
Lamèss Accounting
=================

Foundation module for:
- payout flows
- fiscal handling
- withholding logic
- commission accounting integration
    """,
    'author': 'Solution Consulting S.r.l.',
    'website': 'https://www.solutionconsulting.it',
    'license': 'OPL-1',
    'depends': [
        'account',
        'lamess_base',
        'lamess_commission',
        'lamess_membership',
        'lamess_m3_admin',
        'l10n_it_edi'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/commission_period_views.xml',
        'views/commission_settlement_views.xml',
        'views/commission_settlement_audit_views.xml',
        'views/commission_settlement_wizard_views.xml',
        'views/lamess_config_views.xml',
        'views/payout_request_views.xml',
        'views/res_partner_views.xml',
        'views/l10n_it_edi_export_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
