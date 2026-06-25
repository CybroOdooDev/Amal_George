# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo import fields

@tagged('post_install', '-at_install')
class TestProjectTaskMassUpdate(TransactionCase):
    """Test suite for project.task.mass.update wizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project_src = cls.env['project.project'].create({'name': 'Source Project'})
        cls.project_dest = cls.env['project.project'].create({'name': 'Dest Project'})
        
        cls.user_1 = cls.env['res.users'].create({
            'name': 'Updater 1',
            'login': 'updater1@example.com',
            'email': 'updater1@example.com',
            'groups_id': [(6, 0, cls.env.ref('project.group_project_user').ids)],
        })
        cls.user_2 = cls.env['res.users'].create({
            'name': 'Updater 2',
            'login': 'updater2@example.com',
            'email': 'updater2@example.com',
            'groups_id': [(6, 0, cls.env.ref('project.group_project_user').ids)],
        })

        cls.stage = cls.env['project.task.type'].create({
            'name': 'Folded Stage',
            'fold': True,
        })
        cls.tag = cls.env['project.tags'].create({'name': 'Urgent'})

        cls.task_1 = cls.env['project.task'].create({
            'name': 'Task 1',
            'project_id': cls.project_src.id,
        })
        cls.task_2 = cls.env['project.task'].create({
            'name': 'Task 2',
            'project_id': cls.project_src.id,
        })

    def test_update_task_details(self):
        """Test mass update of task details via wizard."""
        new_deadline = fields.Date.add(fields.Date.today(), days=10)

        wizard = self.env['project.task.mass.update'].with_context(
            active_ids=[self.task_1.id, self.task_2.id]
        ).create({
            'is_update_assign_to': True,
            'user_ids': [(6, 0, [self.user_1.id, self.user_2.id])],
            'is_update_deadline': True,
            'deadline': new_deadline,
            'is_update_project': True,
            'project_id': self.project_dest.id,
            'is_update_stage': True,
            'stage_id': self.stage.id,
            'is_update_tags': True,
            'tag_ids': [(6, 0, self.tag.ids)],
        })
        wizard.update_task_details()

        # Check task 1
        self.assertEqual(self.task_1.project_id, self.project_dest)
        self.assertEqual(fields.Date.to_date(self.task_1.date_deadline), new_deadline)
        self.assertEqual(self.task_1.stage_id, self.stage)
        self.assertIn(self.user_1, self.task_1.user_ids)
        self.assertIn(self.user_2, self.task_1.user_ids)
        self.assertIn(self.tag, self.task_1.tag_ids)

        # Check task 2
        self.assertEqual(self.task_2.project_id, self.project_dest)
        self.assertEqual(fields.Date.to_date(self.task_2.date_deadline), new_deadline)
        self.assertEqual(self.task_2.stage_id, self.stage)
        self.assertIn(self.user_1, self.task_2.user_ids)
        self.assertIn(self.user_2, self.task_2.user_ids)
        self.assertIn(self.tag, self.task_2.tag_ids)
