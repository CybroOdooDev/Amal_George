# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo import fields

@tagged('post_install', '-at_install')
class TestProjectTask(TransactionCase):
    """Test suite for project.task model extensions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['project.project'].create({
            'name': 'Task Test Project',
        })
        cls.user = cls.env['res.users'].create({
            'name': 'Task User',
            'login': 'task_user@example.com',
            'email': 'task_user@example.com',
            'groups_id': [(6, 0, cls.env.ref('project.group_project_user').ids)],
        })
        cls.stage_active = cls.env['project.task.type'].create({
            'name': 'Active Stage',
            'user_ids': [(6, 0, cls.user.ids)],
        })
        cls.stage_done = cls.env['project.task.type'].create({
            'name': 'Done',
        })
        cls.task = cls.env['project.task'].create({
            'name': 'Task Test 1',
            'project_id': cls.project.id,
            'user_ids': [(6, 0, cls.user.ids)],
            'date_deadline': fields.Date.subtract(fields.Date.today(), days=2),
            'stage_id': cls.stage_active.id,
        })
        cls.checklist = cls.env['project.task.checklist'].create({
            'name': 'Verify Task',
            'description': 'Description for Verify',
        })
        cls.template = cls.env['project.task.checklist.template'].create({
            'name': 'Task Checklist Template',
            'checklist_ids': [(6, 0, cls.checklist.ids)],
        })

    def test_task_overdue_notification(self):
        """Test task_overdue_notification sends emails when enabled."""
        self.env['ir.config_parameter'].sudo().set_param(
            'res.config.settings.is_overdue_notification', True
        )
        self.env['mail.mail'].search([]).unlink()

        # Run scheduled notification
        self.env['project.task'].task_overdue_notification()

        # Mail should be generated
        mails = self.env['mail.mail'].search([])
        self.assertTrue(len(mails) >= 1)

    def test_get_user_emails(self):
        """Test _get_user_emails returns correct user logins for overdue tasks."""
        emails = self.task._get_user_emails()
        self.assertIn('task_user@example.com', emails)

        # Move to Done stage, should not be included
        self.task.stage_id = self.stage_done.id
        emails_after = self.task._get_user_emails()
        self.assertNotIn('task_user@example.com', emails_after)

    def test_compute_document_count(self):
        """Test _compute_document_count for task."""
        attachment = self.env['ir.attachment'].create({
            'name': 'Task Doc 1',
            'res_model': 'project.task',
            'res_id': self.task.id,
        })
        self.task._compute_document_count()
        self.assertEqual(self.task.document_count, 1)

    def test_button_task_document(self):
        """Test button_task_document action return."""
        action = self.task.button_task_document()
        self.assertEqual(action['res_model'], 'ir.attachment')
        self.assertEqual(action['view_mode'], 'kanban,form')

    def test_task_mass_update(self):
        """Test task_mass_update action return."""
        action = self.task.task_mass_update()
        self.assertEqual(action['res_model'], 'project.task.mass.update')

    def test_onchange_stage_id(self):
        """Test stage_id onchange auto-assigns stage users."""
        self.task.user_ids = False
        self.task.stage_id = self.stage_active.id
        self.task._onchange_stage_id()
        self.assertEqual(self.task.user_ids, self.stage_active.user_ids)

    def test_onchange_checklist_template_ids(self):
        """Test checklist loading via _onchange_checklist_template_ids on task."""
        self.task.checklist_template_ids = [(6, 0, self.template.ids)]
        self.task._onchange_checklist_template_ids()
        self.assertEqual(len(self.task.checklist_info_ids), 1)
        self.assertEqual(self.task.checklist_info_ids[0].checklist_id, self.checklist)
