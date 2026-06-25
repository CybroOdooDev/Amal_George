# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo import fields

@tagged('post_install', '-at_install')
class TestProjectTaskVelocityChartReport(TransactionCase):
    """Test suite for project.velocity.chart.report."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['project.project'].create({
            'name': 'Velocity Project',
        })
        cls.stage_done = cls.env['project.task.type'].create({
            'name': 'Done',
        })
        # Create a task in 'Done' stage
        cls.task_done = cls.env['project.task'].create({
            'name': 'Done Task',
            'project_id': cls.project.id,
            'stage_id': cls.stage_done.id,
            'date_deadline': fields.Date.today(),
        })

    def test_velocity_chart_read_group(self):
        """Test read_group on the velocity chart report."""
        report = self.env['project.velocity.chart.report'].with_context(
            active_id=self.project.id
        )
        res = report.read_group(
            domain=[('project_id', '=', self.project.id)],
            fields=['completed_story_points'],
            groupby=['date']
        )
        self.assertTrue(isinstance(res, list))
        if res:
            self.assertEqual(len(res), 1)
            first_row = res[0]
            # Verify details match the list layout returned by _read_group override
            self.assertEqual(first_row['completed_story_points'], 1) # count
            self.assertIn('Done Task', first_row['date_count']) # completed name
