# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import ValidationError

@tagged('post_install', '-at_install')
class TestProjectTaskChecklistInfo(TransactionCase):
    """Test suite for project.task.checklist.info."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['project.project'].create({
            'name': 'Task Checklist Info Project',
        })
        cls.task = cls.env['project.task'].create({
            'name': 'Checklist Info Task',
            'project_id': cls.project.id,
        })
        cls.checklist = cls.env['project.task.checklist'].create({
            'name': 'Code Review',
            'description': 'Perform a code review',
        })
        cls.template = cls.env['project.task.checklist.template'].create({
            'name': 'Dev Checklist Template',
            'checklist_ids': [(6, 0, cls.checklist.ids)],
        })
        cls.task.checklist_template_ids = [(6, 0, cls.template.ids)]
        
        cls.checklist_info = cls.env['project.task.checklist.info'].create({
            'checklist_id': cls.checklist.id,
            'task_id': cls.task.id,
            'state': 'new',
        })

    def test_action_set_checklist_complete_success(self):
        """Test completing task checklist info updates status and task progress."""
        initial_progress = self.task.checklist_progress
        self.assertEqual(initial_progress, 0.0)

        self.checklist_info.action_set_checklist_complete()
        self.assertEqual(self.checklist_info.state, 'done')
        self.assertAlmostEqual(self.task.checklist_progress, 100.0)

    def test_action_set_checklist_complete_no_template_checklists(self):
        """Test completing checklist when template has no checklists raises ValidationError."""
        empty_template = self.env['project.task.checklist.template'].create({
            'name': 'Empty Checklist Template',
        })
        task_empty = self.env['project.task'].create({
            'name': 'Task with empty template',
            'project_id': self.project.id,
            'checklist_template_ids': [(6, 0, empty_template.ids)]
        })
        info = self.env['project.task.checklist.info'].create({
            'checklist_id': self.checklist.id,
            'task_id': task_empty.id,
            'state': 'new',
        })
        with self.assertRaises(ValidationError):
            info.action_set_checklist_complete()

    def test_action_set_checklist_close(self):
        """Test action_set_checklist_close sets state to cancel."""
        self.checklist_info.action_set_checklist_close()
        self.assertEqual(self.checklist_info.state, 'cancel')
