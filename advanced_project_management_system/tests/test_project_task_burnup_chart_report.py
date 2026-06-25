# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo import fields

@tagged('post_install', '-at_install')
class TestProjectTaskBurnupChartReport(TransactionCase):
    """Test suite for project.task.burnup.chart.report."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['project.project'].create({
            'name': 'Burnup Project',
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

    def test_burnup_chart_read_group(self):
        """Test read_group on the burnup chart report."""
        report = self.env['project.task.burnup.chart.report'].with_context(
            active_id=self.project.id
        )
        # Calling read_group or _read_group directly
        res = report.read_group(
            domain=[('project_id', '=', self.project.id)],
            fields=['completed_count', 'total_count'],
            groupby=['date']
        )
        self.assertTrue(isinstance(res, list))
        # Verify the structure matches our mock data
        if res:
            self.assertEqual(len(res), 1)
            # The structure returned by _read_group override: (month_year, task_names, total_count)
            # Let's inspect the returned data structure.
            first_row = res[0]
            self.assertEqual(first_row['completed_count'], 1)
            self.assertIn('Done Task', first_row['date_count'])
