# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestProjectChecklistInfo(TransactionCase):
    """Test suite for project.checklist.info."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['project.project'].create({
            'name': 'Checklist Test Project',
        })
        cls.checklist = cls.env['project.checklist'].create({
            'name': 'Design Review',
            'description': 'Review design documents',
        })
        cls.checklist_info_1 = cls.env['project.checklist.info'].create({
            'checklist_id': cls.checklist.id,
            'project_id': cls.project.id,
            'state': 'new',
        })
        cls.checklist_info_2 = cls.env['project.checklist.info'].create({
            'checklist_id': cls.checklist.id,
            'project_id': cls.project.id,
            'state': 'progres',
        })

    def test_action_set_checklist_complete(self):
        """Test action_set_checklist_complete updates state and progress."""
        initial_progress = self.project.checklist_progress
        self.assertEqual(initial_progress, 0.0)

        # Complete first checklist info
        self.checklist_info_1.action_set_checklist_complete()
        self.assertEqual(self.checklist_info_1.state, 'done')
        # Total checklist info count is 2, so progress increases by 50%
        self.assertAlmostEqual(self.project.checklist_progress, 50.0)

        # Complete second checklist info
        self.checklist_info_2.action_set_checklist_complete()
        self.assertEqual(self.checklist_info_2.state, 'done')
        self.assertAlmostEqual(self.project.checklist_progress, 100.0)

    def test_action_set_checklist_close(self):
        """Test action_set_checklist_close sets state to cancel."""
        self.checklist_info_1.action_set_checklist_close()
        self.assertEqual(self.checklist_info_1.state, 'cancel')
