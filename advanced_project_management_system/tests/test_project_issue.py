# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestProjectIssue(TransactionCase):
    """Test suite for project.issue."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['project.project'].create({
            'name': 'Issue Test Project',
        })
        cls.task = cls.env['project.task'].create({
            'name': 'Issue Test Task',
            'project_id': cls.project.id,
        })

    def test_create_issue_sequence(self):
        """Test that creating a project issue generates a sequence name."""
        issue = self.env['project.issue'].create({
            'summary': 'Bug in login page',
            'project_id': self.project.id,
            'task_id': self.task.id,
        })
        self.assertIsNotNone(issue.name)
        self.assertNotEqual(issue.name, 'New')
        self.assertNotEqual(issue.name, '')
