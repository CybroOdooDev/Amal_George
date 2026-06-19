# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestPosSaleOngoing(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestPosSaleOngoing, cls).setUpClass()
        # Set external report layout on company to avoid redirect to base.document.layout wizard
        layout = cls.env.ref('web.external_layout_standard', raise_if_not_found=False)
        if layout:
            cls.env.company.external_report_layout_id = layout.id

        cls.pos_config = cls.env['pos.config'].create({'name': 'Test Config'})
        cls.pos_session = cls.env['pos.session'].create({
            'config_id': cls.pos_config.id,
            'user_id': cls.env.user.id,
        })
        cls.pos_session.action_pos_session_open()

    def test_action_generate_report(self):
        """ Test wizard generates expected report action for ongoing session """
        wizard = self.env['pos.sale.ongoing'].create({
            'session_ids': [(6, 0, self.pos_session.ids)]
        })
        action = wizard.action_generate_report()
        # Should now return the actual report action instead of redirecting
        self.assertEqual(action.get('type'), 'ir.actions.report')
        self.assertEqual(action.get('report_name'), 'advanced_pos_reports.report_pos_ongoing_session')
