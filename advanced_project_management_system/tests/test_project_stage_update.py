# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestProjectStageUpdate(TransactionCase):
    """Test suite for project.stage.update wizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project_1 = cls.env['project.project'].create({
            'name': 'Project 1',
        })
        cls.project_2 = cls.env['project.project'].create({
            'name': 'Project 2',
        })
        cls.stage = cls.env['project.project.stage'].create({
            'name': 'In Progress',
        })

    def test_mass_update_project_stage(self):
        """Test mass update of project stage."""
        wizard = self.env['project.stage.update'].with_context(
            active_ids=[self.project_1.id, self.project_2.id]
        ).create({
            'stage_id': self.stage.id,
            'is_update_stage': True,
        })
        wizard.mass_update_project_stage()
        self.assertEqual(self.project_1.project_stage_id, self.stage)
        self.assertEqual(self.project_2.project_stage_id, self.stage)
