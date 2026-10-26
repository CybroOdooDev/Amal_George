# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: K Sai Saran Varma (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo.tests.common import TransactionCase
from odoo.tests import tagged



@tagged('post_install', '-at_install')
class TestProjectProject(TransactionCase):
    """Test cases for the ProjectProject model (project.project extension)."""

    def setUp(self):
        """Set up test data shared across all test methods."""
        super().setUp()
        self.project = self.env['project.project'].create({
            'name': 'Test Sprint Project',
        })

    # ------------------------------------------------------------------
    # action_get_sprint – return value structure
    # ------------------------------------------------------------------

    def test_action_get_sprint_returns_dict(self):
        """action_get_sprint should return a dictionary (window action)."""
        result = self.project.action_get_sprint()
        self.assertIsInstance(
            result, dict,
            "action_get_sprint() must return a dict"
        )

    def test_action_get_sprint_type(self):
        """action_get_sprint should have type 'ir.actions.act_window'."""
        result = self.project.action_get_sprint()
        self.assertEqual(
            result.get('type'), 'ir.actions.act_window',
            "Action type must be 'ir.actions.act_window'"
        )

    def test_action_get_sprint_name(self):
        """action_get_sprint should have name 'Sprints'."""
        result = self.project.action_get_sprint()
        self.assertEqual(
            result.get('name'), 'Sprints',
            "Action name must be 'Sprints'"
        )

    def test_action_get_sprint_res_model(self):
        """action_get_sprint should target model 'project.sprint'."""
        result = self.project.action_get_sprint()
        self.assertEqual(
            result.get('res_model'), 'project.sprint',
            "res_model must be 'project.sprint'"
        )

    def test_action_get_sprint_view_mode(self):
        """action_get_sprint should provide list,form view modes."""
        result = self.project.action_get_sprint()
        self.assertEqual(
            result.get('view_mode'), 'list,form',
            "view_mode must be 'list,form'"
        )

    def test_action_get_sprint_context_has_default_project_id(self):
        """action_get_sprint context must carry default_project_id."""
        result = self.project.action_get_sprint()
        ctx = result.get('context', {})
        self.assertIn(
            'default_project_id', ctx,
            "context must include 'default_project_id'"
        )
        self.assertEqual(
            ctx['default_project_id'], self.project.id,
            "default_project_id must equal the current project's id"
        )

    def test_action_get_sprint_domain_filters_by_project(self):
        """action_get_sprint domain must filter sprints by this project."""
        result = self.project.action_get_sprint()
        domain = result.get('domain', [])
        self.assertIn(
            ('project_id', '=', self.project.id),
            domain,
            "domain must contain a filter on project_id"
        )

    # ------------------------------------------------------------------
    # action_get_sprint – multiple projects isolation
    # ------------------------------------------------------------------

    def test_action_get_sprint_isolated_per_project(self):
        """Each project's action must reference its own id in domain/context."""
        project_b = self.env['project.project'].create({
            'name': 'Another Project',
        })
        result_a = self.project.action_get_sprint()
        result_b = project_b.action_get_sprint()

        self.assertNotEqual(
            result_a['context']['default_project_id'],
            result_b['context']['default_project_id'],
            "Different projects must have different default_project_id values"
        )
        self.assertIn(
            ('project_id', '=', self.project.id),
            result_a['domain'],
        )
        self.assertIn(
            ('project_id', '=', project_b.id),
            result_b['domain'],
        )

    # ------------------------------------------------------------------
    # Model-level smoke tests
    # ------------------------------------------------------------------

    def test_project_inherits_project_project(self):
        """ProjectProject must inherit from 'project.project'."""
        self.assertEqual(
            self.project._name, 'project.project',
            "Model name must be 'project.project'"
        )

    def test_project_can_have_multiple_sprints(self):
        """Multiple sprints can be linked to one project."""
        sprint1 = self.env['project.sprint'].create({
            'name': 'Sprint 1',
            'project_id': self.project.id,
        })
        sprint2 = self.env['project.sprint'].create({
            'name': 'Sprint 2',
            'project_id': self.project.id,
        })
        sprint_ids = self.env['project.sprint'].search(
            [('project_id', '=', self.project.id)]
        )
        self.assertIn(sprint1, sprint_ids)
        self.assertIn(sprint2, sprint_ids)
