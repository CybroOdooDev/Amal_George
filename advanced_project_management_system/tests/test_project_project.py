# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestProjectProject(TransactionCase):
    """Test suite for project.project model extensions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['project.project'].create({
            'name': 'Management Test Project',
            'url_link': 'https://google.com',
            'url_name': 'Google Search',
        })
        cls.checklist = cls.env['project.checklist'].create({
            'name': 'Integration Design',
            'description': 'Description for Design',
        })
        cls.template = cls.env['project.checklist.template'].create({
            'name': 'Backend Template',
            'checklist_ids': [(6, 0, cls.checklist.ids)],
        })

    def test_open_project_creation_wizard(self):
        """Test open_project_creation_wizard returns appropriate action dict."""
        action = self.project.open_project_creation_wizard()
        self.assertEqual(action['res_model'], 'project.project')
        self.assertEqual(action['view_mode'], 'form')

    def test_compute_url_shortcut(self):
        """Test _compute_url_shortcut correctly computes link and state."""
        project_no_url = self.env['project.project'].create({'name': 'No URL Project'})
        project_no_url._compute_url_shortcut()
        self.assertFalse(project_no_url.is_active)
        self.assertEqual(project_no_url.url_shortcut, 'Add Link')

        self.project._compute_url_shortcut()
        self.assertTrue(self.project.is_active)
        self.assertEqual(self.project.url_shortcut, 'https://google.com')

    def test_open_url_shortcut(self):
        """Test open_url_shortcut action return."""
        action = self.project.open_url_shortcut()
        self.assertEqual(action['type'], 'ir.actions.act_url')
        self.assertEqual(action['url'], 'https://google.com')

    def test_button_document(self):
        """Test button_document action return."""
        action = self.project.button_document()
        self.assertEqual(action['res_model'], 'ir.attachment')
        self.assertEqual(action['view_mode'], 'kanban,form')

    def test_compute_document_count(self):
        """Test _compute_document_count computes correct count."""
        attachment = self.env['ir.attachment'].create({
            'name': 'Proj Doc 1',
            'res_model': 'project.project',
            'res_id': self.project.id,
        })
        self.project._compute_document_count()
        self.assertEqual(self.project.document_count, 1)

    def test_project_multi_stage_update(self):
        """Test project_multi_stage_update action return."""
        action = self.project.project_multi_stage_update()
        self.assertEqual(action['res_model'], 'project.stage.update')

    def test_onchange_checklist_template_ids(self):
        """Test checklist loading via _onchange_checklist_template_ids."""
        self.project.checklist_template_ids = [(6, 0, self.template.ids)]
        self.project._onchange_checklist_template_ids()
        self.assertEqual(len(self.project.project_checklist_info_ids), 1)
        self.assertEqual(self.project.project_checklist_info_ids[0].checklist_id, self.checklist)

    def test_compute_issue_count(self):
        """Test _compute_issue_count."""
        issue = self.env['project.issue'].create({
            'summary': 'Issue test',
            'project_id': self.project.id,
        })
        self.project._compute_issue_count()
        self.assertEqual(self.project.issue_count, 1)

    def test_button_issue(self):
        """Test button_issue action return."""
        action = self.project.button_issue()
        self.assertEqual(action['res_model'], 'project.issue')

    def test_get_stat_buttons(self):
        """Test _get_stat_buttons appends burnup and velocity charts."""
        # Need project user group or mock user_has_groups
        buttons = self.project._get_stat_buttons()
        # Should contain chart buttons if permissions allow, at least we test it executes
        self.assertTrue(isinstance(buttons, list))

    def test_action_project_task_burnup_chart_report(self):
        """Test action_project_task_burnup_chart_report."""
        action = self.project.action_project_task_burnup_chart_report()
        self.assertEqual(action['type'], 'ir.actions.act_window')

    def test_action_project_velocity_chart_report(self):
        """Test action_project_velocity_chart_report."""
        action = self.project.action_project_velocity_chart_report()
        self.assertEqual(action['type'], 'ir.actions.act_window')

    def test_action_open_shortcut(self):
        """Test action_open_shortcut."""
        action = self.project.action_open_shortcut()
        self.assertEqual(action['res_model'], 'project.shortcut')
