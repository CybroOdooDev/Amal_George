# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import UserError

@tagged('post_install', '-at_install')
class TestProjectShortcut(TransactionCase):
    """Test suite for project.shortcut wizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['project.project'].create({
            'name': 'Shortcut Target Project',
        })

    def test_default_get(self):
        """Test default_get populates project_id from active_id context."""
        wizard = self.env['project.shortcut'].with_context(active_id=self.project.id).create({
            'name': 'My Link',
            'link': 'https://odoo.com',
        })
        # default_get gets called during create or form load. Let's test default_get directly.
        defaults = self.env['project.shortcut'].with_context(active_id=self.project.id).default_get(['project_id'])
        self.assertEqual(defaults.get('project_id'), self.project.id)

    def test_is_valid_url(self):
        """Test is_valid_url validator."""
        wizard = self.env['project.shortcut']
        self.assertTrue(wizard.is_valid_url('https://google.com'))
        self.assertTrue(wizard.is_valid_url('http://localhost:8069'))
        self.assertFalse(wizard.is_valid_url('not_a_valid_url'))
        self.assertFalse(wizard.is_valid_url('google.com')) # missing scheme

    def test_action_project_shortcut_valid(self):
        """Test wizard updates project with valid URL."""
        wizard = self.env['project.shortcut'].create({
            'name': 'Main Wiki',
            'link': 'https://wiki.company.com',
            'project_id': self.project.id,
        })
        wizard.action_project_shortcut()
        self.assertEqual(self.project.url_link, 'https://wiki.company.com')
        self.assertEqual(self.project.url_name, 'Main Wiki')
        self.assertTrue(self.project.is_active)

    def test_action_project_shortcut_invalid(self):
        """Test wizard raises UserError on invalid URL."""
        wizard = self.env['project.shortcut'].create({
            'name': 'Bad Link',
            'link': 'invalid-url',
            'project_id': self.project.id,
        })
        with self.assertRaises(UserError):
            wizard.action_project_shortcut()
