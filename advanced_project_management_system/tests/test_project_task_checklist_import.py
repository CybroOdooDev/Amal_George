# -*- coding: utf-8 -*-
import base64
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestProjectTaskChecklistImport(TransactionCase):
    """Test suite for project.task.checklist.import wizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

    def test_import_custom_checklist_csv(self):
        """Test importing task checklists using CSV."""
        csv_data = "Name,Description\nCSV Checklist 1,CSV Description 1\nCSV Checklist 2,CSV Description 2"
        encoded_csv = base64.b64encode(csv_data.encode('utf-8'))

        initial_count = self.env['project.task.checklist'].search_count([])

        wizard = self.env['project.task.checklist.import'].create({
            'file': encoded_csv,
            'file_type': 'csv',
            'company_id': self.company.id,
        })
        wizard.import_custom_checklist()

        # We expect 2 new checklists to be created
        new_count = self.env['project.task.checklist'].search_count([])
        self.assertEqual(new_count - initial_count, 2)

        checklist1 = self.env['project.task.checklist'].search([('name', '=', 'CSV Checklist 1')])
        self.assertTrue(checklist1)
        self.assertEqual(checklist1.description, 'CSV Description 1')
