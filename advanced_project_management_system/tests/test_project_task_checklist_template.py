# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestProjectTaskChecklistTemplate(TransactionCase):
    """Test suite for project.task.checklist.template."""

    def test_create_template_and_checklists(self):
        """Test template creation and link with checklists."""
        checklist_1 = self.env['project.task.checklist'].create({
            'name': 'Task Checklist 1',
            'description': 'Description 1',
        })
        checklist_2 = self.env['project.task.checklist'].create({
            'name': 'Task Checklist 2',
            'description': 'Description 2',
        })
        template = self.env['project.task.checklist.template'].create({
            'name': 'Custom Task Template',
            'checklist_ids': [(6, 0, [checklist_1.id, checklist_2.id])],
        })
        self.assertEqual(template.name, 'Custom Task Template')
        self.assertEqual(len(template.checklist_ids), 2)
        self.assertIn(checklist_1, template.checklist_ids)
        self.assertIn(checklist_2, template.checklist_ids)
