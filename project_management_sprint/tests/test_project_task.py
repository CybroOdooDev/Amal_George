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
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestProjectTask(TransactionCase):
    """Test cases for the ProjectTask model (project.task extension)."""

    def setUp(self):
        """Set up shared test data."""
        super().setUp()
        _logger.info("[TestProjectTask] Setting up test data")
        self.project = self.env['project.project'].create({
            'name': 'Task Test Project',
        })
        self.sprint = self.env['project.sprint'].create({
            'name': 'Test Sprint',
            'project_id': self.project.id,
            'start_date': datetime.now(),
            'end_date': datetime.now() + timedelta(days=14),
        })
        self.stage = self.env['project.task.type'].create({
            'name': 'In Progress',
        })
        self.task = self.env['project.task'].create({
            'name': 'Base Task',
            'project_id': self.project.id,
            'stage_id': self.stage.id,
        })
        self.blocking_task = self.env['project.task'].create({
            'name': 'Blocking Task',
            'project_id': self.project.id,
            'stage_id': self.stage.id,
        })
        _logger.info("[TestProjectTask] Created project id=%s, sprint id=%s, "
                     "task id=%s, blocking_task id=%s",
                     self.project.id, self.sprint.id,
                     self.task.id, self.blocking_task.id)

    # ------------------------------------------------------------------
    # Field smoke tests
    # ------------------------------------------------------------------

    def test_task_model_name(self):
        """Task model name must be 'project.task'."""
        _logger.info("[TestProjectTask] test_task_model_name: start")
        self.assertEqual(self.task._name, 'project.task')
        _logger.info("[TestProjectTask] test_task_model_name: PASSED (_name=%s)", self.task._name)

    def test_task_sprint_id_field_exists(self):
        """Task must have a sprint_id Many2one field."""
        _logger.info("[TestProjectTask] test_task_sprint_id_field_exists: start")
        self.assertIn('sprint_id', self.task._fields)
        _logger.info("[TestProjectTask] test_task_sprint_id_field_exists: PASSED")

    def test_task_linked_issue_field_exists(self):
        """Task must have a linked_issue Selection field."""
        _logger.info("[TestProjectTask] test_task_linked_issue_field_exists: start")
        self.assertIn('linked_issue', self.task._fields)
        _logger.info("[TestProjectTask] test_task_linked_issue_field_exists: PASSED")

    def test_task_issue_task_id_field_exists(self):
        """Task must have an issue_task_id Many2one field."""
        _logger.info("[TestProjectTask] test_task_issue_task_id_field_exists: start")
        self.assertIn('issue_task_id', self.task._fields)
        _logger.info("[TestProjectTask] test_task_issue_task_id_field_exists: PASSED")

    # ------------------------------------------------------------------
    # sprint_id assignment
    # ------------------------------------------------------------------

    def test_task_sprint_id_defaults_to_false(self):
        """Task sprint_id should be False when not explicitly set."""
        _logger.info("[TestProjectTask] test_task_sprint_id_defaults_to_false: start")
        self.assertFalse(self.task.sprint_id, "sprint_id must be False when not assigned")
        _logger.info("[TestProjectTask] test_task_sprint_id_defaults_to_false: PASSED")

    def test_task_sprint_id_can_be_assigned(self):
        """Task sprint_id should accept a valid sprint in the same project."""
        _logger.info("[TestProjectTask] test_task_sprint_id_can_be_assigned: start")
        self.task.write({'sprint_id': self.sprint.id})
        self.assertEqual(self.task.sprint_id, self.sprint,
                         "sprint_id must match the assigned sprint")
        _logger.info("[TestProjectTask] test_task_sprint_id_can_be_assigned: PASSED (sprint_id=%s)", self.task.sprint_id.id)

    def test_task_sprint_id_can_be_created_with_sprint(self):
        """Task can be created with a sprint_id already set."""
        _logger.info("[TestProjectTask] test_task_sprint_id_can_be_created_with_sprint: start")
        task_with_sprint = self.env['project.task'].create({
            'name': 'Sprinted Task',
            'project_id': self.project.id,
            'stage_id': self.stage.id,
            'sprint_id': self.sprint.id,
        })
        self.assertEqual(task_with_sprint.sprint_id, self.sprint)
        _logger.info("[TestProjectTask] test_task_sprint_id_can_be_created_with_sprint: PASSED (task id=%s)", task_with_sprint.id)

    def test_task_sprint_id_can_be_cleared(self):
        """sprint_id can be removed (set back to False) after being assigned."""
        _logger.info("[TestProjectTask] test_task_sprint_id_can_be_cleared: start")
        self.task.write({'sprint_id': self.sprint.id})
        self.task.write({'sprint_id': False})
        self.assertFalse(self.task.sprint_id)
        _logger.info("[TestProjectTask] test_task_sprint_id_can_be_cleared: PASSED")

    # ------------------------------------------------------------------
    # linked_issue & issue_task_id
    # ------------------------------------------------------------------

    def test_linked_issue_defaults_to_false(self):
        """linked_issue must default to False when not set."""
        _logger.info("[TestProjectTask] test_linked_issue_defaults_to_false: start")
        self.assertFalse(self.task.linked_issue, "linked_issue must be False by default")
        _logger.info("[TestProjectTask] test_linked_issue_defaults_to_false: PASSED")

    def test_linked_issue_can_be_set(self):
        """linked_issue can be set to 'is_blocked_by'."""
        _logger.info("[TestProjectTask] test_linked_issue_can_be_set: start")
        self.task.write({
            'linked_issue': 'is_blocked_by',
            'issue_task_id': self.blocking_task.id,
        })
        self.assertEqual(self.task.linked_issue, 'is_blocked_by')
        self.assertEqual(self.task.issue_task_id, self.blocking_task)
        _logger.info("[TestProjectTask] test_linked_issue_can_be_set: PASSED (linked_issue=%s, issue_task_id=%s)",
                     self.task.linked_issue, self.task.issue_task_id.id)

    def test_issue_task_id_defaults_to_false(self):
        """issue_task_id must default to False when not set."""
        _logger.info("[TestProjectTask] test_issue_task_id_defaults_to_false: start")
        self.assertFalse(self.task.issue_task_id, "issue_task_id must be False by default")
        _logger.info("[TestProjectTask] test_issue_task_id_defaults_to_false: PASSED")

    # ------------------------------------------------------------------
    # _check_stage_id constraint
    # ------------------------------------------------------------------

    def test_stage_change_raises_error_when_linked_issue_set(self):
        """Changing stage on a task with linked_issue should raise UserError."""
        _logger.info("[TestProjectTask] test_stage_change_raises_error_when_linked_issue_set: start")
        self.task.write({
            'linked_issue': 'is_blocked_by',
            'issue_task_id': self.blocking_task.id,
        })
        new_stage = self.env['project.task.type'].create({'name': 'Done'})
        with self.assertRaises(UserError):
            self.task.write({'stage_id': new_stage.id})
        _logger.info("[TestProjectTask] test_stage_change_raises_error_when_linked_issue_set: PASSED (UserError raised as expected)")

    def test_stage_change_allowed_when_no_linked_issue(self):
        """Changing stage on a task without linked_issue should succeed."""
        _logger.info("[TestProjectTask] test_stage_change_allowed_when_no_linked_issue: start")
        new_stage = self.env['project.task.type'].create({'name': 'Done Stage'})
        self.task.write({'stage_id': new_stage.id})
        self.assertEqual(self.task.stage_id, new_stage)
        _logger.info("[TestProjectTask] test_stage_change_allowed_when_no_linked_issue: PASSED (new stage_id=%s)", new_stage.id)

    def test_stage_change_error_message_is_descriptive(self):
        """UserError on blocked stage change should contain a meaningful message."""
        _logger.info("[TestProjectTask] test_stage_change_error_message_is_descriptive: start")
        self.task.write({
            'linked_issue': 'is_blocked_by',
            'issue_task_id': self.blocking_task.id,
        })
        new_stage = self.env['project.task.type'].create({'name': 'Archived'})
        try:
            self.task.write({'stage_id': new_stage.id})
            self.fail("UserError was not raised")
        except UserError as exc:
            self.assertTrue(str(exc.args[0]), "UserError must carry a non-empty message")
            _logger.info("[TestProjectTask] test_stage_change_error_message_is_descriptive: PASSED (msg=%s)", exc.args[0])

    def test_linked_issue_cleared_allows_stage_change(self):
        """After clearing linked_issue, stage change must succeed."""
        _logger.info("[TestProjectTask] test_linked_issue_cleared_allows_stage_change: start")
        new_stage = self.env['project.task.type'].create({'name': 'Review'})
        self.task.write({
            'linked_issue': 'is_blocked_by',
            'issue_task_id': self.blocking_task.id,
        })
        self.task.write({'linked_issue': False, 'issue_task_id': False})
        self.task.write({'stage_id': new_stage.id})
        self.assertEqual(self.task.stage_id, new_stage)
        _logger.info("[TestProjectTask] test_linked_issue_cleared_allows_stage_change: PASSED")

    # ------------------------------------------------------------------
    # Multiple tasks in same sprint
    # ------------------------------------------------------------------

    def test_multiple_tasks_can_share_same_sprint(self):
        """Multiple tasks can belong to the same sprint."""
        _logger.info("[TestProjectTask] test_multiple_tasks_can_share_same_sprint: start")
        task2 = self.env['project.task'].create({
            'name': 'Second Sprinted Task',
            'project_id': self.project.id,
            'stage_id': self.stage.id,
            'sprint_id': self.sprint.id,
        })
        self.task.write({'sprint_id': self.sprint.id})
        sprint_tasks = self.env['project.task'].search(
            [('sprint_id', '=', self.sprint.id)])
        self.assertIn(self.task, sprint_tasks)
        self.assertIn(task2, sprint_tasks)
        _logger.info("[TestProjectTask] test_multiple_tasks_can_share_same_sprint: PASSED (%d tasks in sprint)", len(sprint_tasks))

    def test_backlog_tasks_have_no_sprint(self):
        """Tasks without a sprint should appear in backlog queries."""
        _logger.info("[TestProjectTask] test_backlog_tasks_have_no_sprint: start")
        backlog_tasks = self.env['project.task'].search([
            ('project_id', '=', self.project.id),
            ('sprint_id', '=', False),
        ])
        self.assertIn(self.task, backlog_tasks)
        _logger.info("[TestProjectTask] test_backlog_tasks_have_no_sprint: PASSED (%d backlog tasks)", len(backlog_tasks))

    def test_task_sprint_belongs_to_same_project(self):
        """A sprint linked to a task should belong to the same project."""
        _logger.info("[TestProjectTask] test_task_sprint_belongs_to_same_project: start")
        self.task.write({'sprint_id': self.sprint.id})
        self.assertEqual(self.task.sprint_id.project_id, self.task.project_id,
                         "Sprint project must match the task's project")
        _logger.info("[TestProjectTask] test_task_sprint_belongs_to_same_project: PASSED")
