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
import logging
from datetime import datetime, timedelta

from odoo.tests.common import TransactionCase
from odoo.tests import tagged

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestProjectSprint(TransactionCase):
    """Test cases for the ProjectSprint model (project.sprint)."""

    def setUp(self):
        """Set up shared test data."""
        super().setUp()
        _logger.info("[TestProjectSprint] Setting up test data")
        self.project = self.env['project.project'].create({
            'name': 'Test Project for Sprints',
        })
        self.now = datetime.now()
        self.sprint = self.env['project.sprint'].create({
            'name': 'Sprint Alpha',
            'sprint_goal': 'Deliver the MVP',
            'start_date': self.now,
            'end_date': self.now + timedelta(days=14),
            'project_id': self.project.id,
        })
        _logger.info("[TestProjectSprint] Created project id=%s, sprint id=%s name='%s'",
                     self.project.id, self.sprint.id, self.sprint.name)

    # ------------------------------------------------------------------
    # Model / field smoke tests
    # ------------------------------------------------------------------

    def test_sprint_model_name(self):
        """Sprint model name must be 'project.sprint'."""
        _logger.info("[TestProjectSprint] test_sprint_model_name: start")
        self.assertEqual(self.sprint._name, 'project.sprint')
        _logger.info("[TestProjectSprint] test_sprint_model_name: PASSED (_name=%s)", self.sprint._name)

    def test_sprint_creation_with_required_fields(self):
        """A sprint can be created with a name and linked project."""
        _logger.info("[TestProjectSprint] test_sprint_creation_with_required_fields: start")
        self.assertTrue(self.sprint.id, "Sprint should be persisted (have an id)")
        self.assertEqual(self.sprint.name, 'Sprint Alpha')
        _logger.info("[TestProjectSprint] test_sprint_creation_with_required_fields: PASSED (id=%s)", self.sprint.id)

    def test_sprint_default_state_is_to_start(self):
        """Newly created sprint should default to 'to_start' state."""
        _logger.info("[TestProjectSprint] test_sprint_default_state_is_to_start: start")
        self.assertEqual(self.sprint.state, 'to_start',
                         "Default state must be 'to_start'")
        _logger.info("[TestProjectSprint] test_sprint_default_state_is_to_start: PASSED (state=%s)", self.sprint.state)

    def test_sprint_goal_stored_correctly(self):
        """Sprint goal text should be stored and retrieved correctly."""
        _logger.info("[TestProjectSprint] test_sprint_goal_stored_correctly: start")
        self.assertEqual(self.sprint.sprint_goal, 'Deliver the MVP')
        _logger.info("[TestProjectSprint] test_sprint_goal_stored_correctly: PASSED")

    def test_sprint_project_id_set(self):
        """Sprint must be linked to its project."""
        _logger.info("[TestProjectSprint] test_sprint_project_id_set: start")
        self.assertEqual(self.sprint.project_id, self.project)
        _logger.info("[TestProjectSprint] test_sprint_project_id_set: PASSED (project_id=%s)", self.sprint.project_id.id)

    def test_sprint_start_and_end_dates(self):
        """Start date and end date should be stored correctly."""
        _logger.info("[TestProjectSprint] test_sprint_start_and_end_dates: start")
        self.assertTrue(self.sprint.start_date, "start_date must not be empty")
        self.assertTrue(self.sprint.end_date, "end_date must not be empty")
        self.assertGreater(self.sprint.end_date, self.sprint.start_date,
                           "end_date must be after start_date")
        _logger.info("[TestProjectSprint] test_sprint_start_and_end_dates: PASSED")

    # ------------------------------------------------------------------
    # State transition tests
    # ------------------------------------------------------------------

    def test_action_start_sprint_sets_ongoing(self):
        """action_start_sprint should transition state to 'ongoing'."""
        _logger.info("[TestProjectSprint] test_action_start_sprint_sets_ongoing: start")
        self.sprint.action_start_sprint()
        self.assertEqual(self.sprint.state, 'ongoing',
                         "State must be 'ongoing' after action_start_sprint()")
        _logger.info("[TestProjectSprint] test_action_start_sprint_sets_ongoing: PASSED (state=%s)", self.sprint.state)

    def test_action_finish_sprint_sets_completed(self):
        """action_finish_sprint should transition state to 'completed'."""
        _logger.info("[TestProjectSprint] test_action_finish_sprint_sets_completed: start")
        self.sprint.action_start_sprint()
        self.sprint.action_finish_sprint()
        self.assertEqual(self.sprint.state, 'completed',
                         "State must be 'completed' after action_finish_sprint()")
        _logger.info("[TestProjectSprint] test_action_finish_sprint_sets_completed: PASSED (state=%s)", self.sprint.state)

    def test_action_reset_states_sets_to_start(self):
        """action_reset_states should revert state back to 'to_start'."""
        _logger.info("[TestProjectSprint] test_action_reset_states_sets_to_start: start")
        self.sprint.action_start_sprint()
        self.sprint.action_finish_sprint()
        self.sprint.action_reset_states()
        self.assertEqual(self.sprint.state, 'to_start',
                         "State must be 'to_start' after action_reset_states()")
        _logger.info("[TestProjectSprint] test_action_reset_states_sets_to_start: PASSED (state=%s)", self.sprint.state)

    def test_full_state_lifecycle(self):
        """Full lifecycle: to_start → ongoing → completed → to_start."""
        _logger.info("[TestProjectSprint] test_full_state_lifecycle: start")
        self.assertEqual(self.sprint.state, 'to_start')
        self.sprint.action_start_sprint()
        self.assertEqual(self.sprint.state, 'ongoing')
        _logger.info("[TestProjectSprint] test_full_state_lifecycle: ongoing OK")
        self.sprint.action_finish_sprint()
        self.assertEqual(self.sprint.state, 'completed')
        _logger.info("[TestProjectSprint] test_full_state_lifecycle: completed OK")
        self.sprint.action_reset_states()
        self.assertEqual(self.sprint.state, 'to_start')
        _logger.info("[TestProjectSprint] test_full_state_lifecycle: PASSED")

    def test_reset_from_to_start_stays_to_start(self):
        """Resetting a sprint already in 'to_start' keeps it in 'to_start'."""
        _logger.info("[TestProjectSprint] test_reset_from_to_start_stays_to_start: start")
        self.sprint.action_reset_states()
        self.assertEqual(self.sprint.state, 'to_start')
        _logger.info("[TestProjectSprint] test_reset_from_to_start_stays_to_start: PASSED")

    # ------------------------------------------------------------------
    # action_get_tasks
    # ------------------------------------------------------------------

    def test_action_get_tasks_returns_dict(self):
        """action_get_tasks must return a window-action dictionary."""
        _logger.info("[TestProjectSprint] test_action_get_tasks_returns_dict: start")
        result = self.sprint.action_get_tasks()
        self.assertIsInstance(result, dict)
        _logger.info("[TestProjectSprint] test_action_get_tasks_returns_dict: PASSED")

    def test_action_get_tasks_type(self):
        """action_get_tasks type must be 'ir.actions.act_window'."""
        _logger.info("[TestProjectSprint] test_action_get_tasks_type: start")
        result = self.sprint.action_get_tasks()
        self.assertEqual(result.get('type'), 'ir.actions.act_window')
        _logger.info("[TestProjectSprint] test_action_get_tasks_type: PASSED (type=%s)", result.get('type'))

    def test_action_get_tasks_res_model(self):
        """action_get_tasks res_model must be 'project.task'."""
        _logger.info("[TestProjectSprint] test_action_get_tasks_res_model: start")
        result = self.sprint.action_get_tasks()
        self.assertEqual(result.get('res_model'), 'project.task')
        _logger.info("[TestProjectSprint] test_action_get_tasks_res_model: PASSED")

    def test_action_get_tasks_name(self):
        """action_get_tasks name must be 'Tasks'."""
        _logger.info("[TestProjectSprint] test_action_get_tasks_name: start")
        result = self.sprint.action_get_tasks()
        self.assertEqual(result.get('name'), 'Tasks')
        _logger.info("[TestProjectSprint] test_action_get_tasks_name: PASSED")

    def test_action_get_tasks_domain_contains_sprint_id(self):
        """action_get_tasks domain must filter by current sprint id."""
        _logger.info("[TestProjectSprint] test_action_get_tasks_domain_contains_sprint_id: start")
        result = self.sprint.action_get_tasks()
        domain = result.get('domain', [])
        self.assertIn(('sprint_id', '=', self.sprint.id), domain,
                      "domain must filter by sprint_id")
        _logger.info("[TestProjectSprint] test_action_get_tasks_domain_contains_sprint_id: PASSED (domain=%s)", domain)

    def test_action_get_tasks_domain_contains_project_id(self):
        """action_get_tasks domain must filter by the project id."""
        _logger.info("[TestProjectSprint] test_action_get_tasks_domain_contains_project_id: start")
        result = self.sprint.action_get_tasks()
        domain = result.get('domain', [])
        self.assertIn(('project_id', '=', self.sprint.project_id.id), domain,
                      "domain must filter by project_id")
        _logger.info("[TestProjectSprint] test_action_get_tasks_domain_contains_project_id: PASSED")

    def test_action_get_tasks_has_views(self):
        """action_get_tasks must define a 'views' key."""
        _logger.info("[TestProjectSprint] test_action_get_tasks_has_views: start")
        result = self.sprint.action_get_tasks()
        self.assertIn('views', result, "'views' key must be present")
        self.assertTrue(result['views'], "'views' must not be empty")
        _logger.info("[TestProjectSprint] test_action_get_tasks_has_views: PASSED")

    # ------------------------------------------------------------------
    # action_get_backlogs
    # ------------------------------------------------------------------

    def test_action_get_backlogs_returns_dict(self):
        """action_get_backlogs must return a window-action dictionary."""
        _logger.info("[TestProjectSprint] test_action_get_backlogs_returns_dict: start")
        result = self.sprint.action_get_backlogs()
        self.assertIsInstance(result, dict)
        _logger.info("[TestProjectSprint] test_action_get_backlogs_returns_dict: PASSED")

    def test_action_get_backlogs_type(self):
        """action_get_backlogs type must be 'ir.actions.act_window'."""
        _logger.info("[TestProjectSprint] test_action_get_backlogs_type: start")
        result = self.sprint.action_get_backlogs()
        self.assertEqual(result.get('type'), 'ir.actions.act_window')
        _logger.info("[TestProjectSprint] test_action_get_backlogs_type: PASSED")

    def test_action_get_backlogs_res_model(self):
        """action_get_backlogs res_model must be 'project.task'."""
        _logger.info("[TestProjectSprint] test_action_get_backlogs_res_model: start")
        result = self.sprint.action_get_backlogs()
        self.assertEqual(result.get('res_model'), 'project.task')
        _logger.info("[TestProjectSprint] test_action_get_backlogs_res_model: PASSED")

    def test_action_get_backlogs_name(self):
        """action_get_backlogs name must be 'Backlogs'."""
        _logger.info("[TestProjectSprint] test_action_get_backlogs_name: start")
        result = self.sprint.action_get_backlogs()
        self.assertEqual(result.get('name'), 'Backlogs')
        _logger.info("[TestProjectSprint] test_action_get_backlogs_name: PASSED")

    def test_action_get_backlogs_domain_no_sprint(self):
        """action_get_backlogs domain must require sprint_id = False."""
        _logger.info("[TestProjectSprint] test_action_get_backlogs_domain_no_sprint: start")
        result = self.sprint.action_get_backlogs()
        domain = result.get('domain', [])
        self.assertIn(('sprint_id', '=', False), domain,
                      "Backlog domain must filter tasks with no sprint")
        _logger.info("[TestProjectSprint] test_action_get_backlogs_domain_no_sprint: PASSED")

    def test_action_get_backlogs_domain_contains_project_id(self):
        """action_get_backlogs domain must filter by project id."""
        _logger.info("[TestProjectSprint] test_action_get_backlogs_domain_contains_project_id: start")
        result = self.sprint.action_get_backlogs()
        domain = result.get('domain', [])
        self.assertIn(('project_id', '=', self.sprint.project_id.id), domain,
                      "domain must filter by project_id")
        _logger.info("[TestProjectSprint] test_action_get_backlogs_domain_contains_project_id: PASSED")

    # ------------------------------------------------------------------
    # action_get_all_tasks
    # ------------------------------------------------------------------

    def test_action_get_all_tasks_returns_dict(self):
        """action_get_all_tasks must return a window-action dictionary."""
        _logger.info("[TestProjectSprint] test_action_get_all_tasks_returns_dict: start")
        result = self.sprint.action_get_all_tasks()
        self.assertIsInstance(result, dict)
        _logger.info("[TestProjectSprint] test_action_get_all_tasks_returns_dict: PASSED")

    def test_action_get_all_tasks_type(self):
        """action_get_all_tasks type must be 'ir.actions.act_window'."""
        _logger.info("[TestProjectSprint] test_action_get_all_tasks_type: start")
        result = self.sprint.action_get_all_tasks()
        self.assertEqual(result.get('type'), 'ir.actions.act_window')
        _logger.info("[TestProjectSprint] test_action_get_all_tasks_type: PASSED")

    def test_action_get_all_tasks_res_model(self):
        """action_get_all_tasks res_model must be 'project.task'."""
        _logger.info("[TestProjectSprint] test_action_get_all_tasks_res_model: start")
        result = self.sprint.action_get_all_tasks()
        self.assertEqual(result.get('res_model'), 'project.task')
        _logger.info("[TestProjectSprint] test_action_get_all_tasks_res_model: PASSED")

    def test_action_get_all_tasks_name(self):
        """action_get_all_tasks name must be 'All Tasks'."""
        _logger.info("[TestProjectSprint] test_action_get_all_tasks_name: start")
        result = self.sprint.action_get_all_tasks()
        self.assertEqual(result.get('name'), 'All Tasks')
        _logger.info("[TestProjectSprint] test_action_get_all_tasks_name: PASSED")

    def test_action_get_all_tasks_domain_contains_project_id(self):
        """action_get_all_tasks domain must filter by project id."""
        _logger.info("[TestProjectSprint] test_action_get_all_tasks_domain_contains_project_id: start")
        result = self.sprint.action_get_all_tasks()
        domain = result.get('domain', [])
        self.assertIn(('project_id', '=', self.sprint.project_id.id), domain,
                      "domain must filter by project_id")
        _logger.info("[TestProjectSprint] test_action_get_all_tasks_domain_contains_project_id: PASSED")

    def test_action_get_all_tasks_has_no_sprint_filter(self):
        """action_get_all_tasks must NOT restrict by sprint_id."""
        _logger.info("[TestProjectSprint] test_action_get_all_tasks_has_no_sprint_filter: start")
        result = self.sprint.action_get_all_tasks()
        domain = result.get('domain', [])
        sprint_filters = [
            cond for cond in domain
            if isinstance(cond, (list, tuple)) and cond[0] == 'sprint_id'
        ]
        self.assertFalse(sprint_filters,
                         "action_get_all_tasks domain should not filter by sprint_id")
        _logger.info("[TestProjectSprint] test_action_get_all_tasks_has_no_sprint_filter: PASSED")

    def test_action_get_all_tasks_has_views(self):
        """action_get_all_tasks must define a 'views' key."""
        _logger.info("[TestProjectSprint] test_action_get_all_tasks_has_views: start")
        result = self.sprint.action_get_all_tasks()
        self.assertIn('views', result, "'views' key must be present")
        self.assertTrue(result['views'], "'views' must not be empty")
        _logger.info("[TestProjectSprint] test_action_get_all_tasks_has_views: PASSED")

    # ------------------------------------------------------------------
    # Multiple sprints in a project
    # ------------------------------------------------------------------

    def test_multiple_sprints_in_same_project(self):
        """Multiple sprints can coexist under one project."""
        _logger.info("[TestProjectSprint] test_multiple_sprints_in_same_project: start")
        sprint2 = self.env['project.sprint'].create({
            'name': 'Sprint Beta',
            'project_id': self.project.id,
            'start_date': self.now + timedelta(days=15),
            'end_date': self.now + timedelta(days=29),
        })
        sprints = self.env['project.sprint'].search(
            [('project_id', '=', self.project.id)])
        self.assertIn(self.sprint, sprints)
        self.assertIn(sprint2, sprints)
        _logger.info("[TestProjectSprint] test_multiple_sprints_in_same_project: PASSED (%d sprints)", len(sprints))

    def test_sprint_without_project_is_allowed(self):
        """A sprint can be created without a project (project_id is optional)."""
        _logger.info("[TestProjectSprint] test_sprint_without_project_is_allowed: start")
        sprint_no_proj = self.env['project.sprint'].create({'name': 'Orphan Sprint'})
        self.assertFalse(sprint_no_proj.project_id)
        _logger.info("[TestProjectSprint] test_sprint_without_project_is_allowed: PASSED (id=%s)", sprint_no_proj.id)
