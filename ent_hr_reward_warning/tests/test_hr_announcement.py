# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(odoo@cybrosys.com)
#
#    This program is under the terms of the Odoo Proprietary License v1.0(OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the
#    Software or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NON INFRINGEMENT. IN NO EVENT SHALL
#    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,ARISING
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
###############################################################################
from datetime import timedelta
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestHrAnnouncement(TransactionCase):
    """ Test suite for HR Announcement module models and features. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.today()
        cls.department = cls.env['hr.department'].create({
            'name': 'Research & Development',
        })
        cls.job_position = cls.env['hr.job'].create({
            'name': 'Software Engineer',
        })
        cls.employee_1 = cls.env['hr.employee'].create({
            'name': 'Alice Developer',
            'department_id': cls.department.id,
            'job_id': cls.job_position.id,
        })
        cls.employee_2 = cls.env['hr.employee'].create({
            'name': 'Bob Designer',
        })

    def test_01_general_announcement_sequence_and_defaults(self):
        """ Verify sequence generation and defaults for General Announcements. """
        announcement = self.env['hr.announcement'].create({
            'announcement_reason': 'Annual Company Outing',
            'is_announcement': True,
        })
        self.assertTrue(announcement.name.startswith('GA'))
        self.assertEqual(announcement.state, 'draft')
        self.assertEqual(announcement.company_id, self.env.company)
        self.assertEqual(announcement.requested_date, self.today)
        self.assertEqual(announcement.date_start, self.today)
        self.assertEqual(announcement.date_end, self.today)

    def test_02_targeted_announcement_sequence(self):
        """ Verify sequence generation for targeted announcements. """
        announcement = self.env['hr.announcement'].create({
            'announcement_reason': 'Employee Recognition',
            'is_announcement': False,
            'announcement_type': 'employee',
            'employee_ids': [(4, self.employee_1.id)],
        })
        self.assertTrue(announcement.name.startswith('AN'))

    def test_03_custom_name_announcement(self):
        """ Verify that explicitly provided name is preserved upon creation. """
        announcement = self.env['hr.announcement'].create({
            'name': 'CUSTOM-NOTICE-001',
            'announcement_reason': 'Special Notice',
            'is_announcement': True,
        })
        self.assertEqual(announcement.name, 'CUSTOM-NOTICE-001')

    def test_04_date_validation_constraint(self):
        """ Verify that start date after end date raises ValidationError. """
        with self.assertRaises(ValidationError):
            self.env['hr.announcement'].create({
                'announcement_reason': 'Invalid Schedule Notice',
                'date_start': self.today + timedelta(days=5),
                'date_end': self.today,
            })

        # Valid dates should succeed without error
        announcement = self.env['hr.announcement'].create({
            'announcement_reason': 'Valid Schedule Notice',
            'date_start': self.today,
            'date_end': self.today + timedelta(days=5),
        })
        self.assertTrue(announcement.id)

    def test_05_workflow_transitions(self):
        """ Test announcement workflow actions: send, approve, refuse. """
        announcement = self.env['hr.announcement'].create({
            'announcement_reason': 'Policy Update',
            'is_announcement': True,
        })
        self.assertEqual(announcement.state, 'draft')

        # Send for approval
        announcement.action_send()
        self.assertEqual(announcement.state, 'to_approve')

        # Approve
        announcement.action_approve()
        self.assertEqual(announcement.state, 'approved')

        # Refuse workflow on a second record
        announcement_2 = self.env['hr.announcement'].create({
            'announcement_reason': 'Office Maintenance Notice',
            'is_announcement': True,
        })
        announcement_2.action_send()
        announcement_2.action_reject()
        self.assertEqual(announcement_2.state, 'rejected')

    def test_06_expiry_cron_action(self):
        """ Verify that the cron job marks past non-rejected announcements as expired. """
        past_date = self.today - timedelta(days=10)
        future_date = self.today + timedelta(days=10)

        # Expired approved announcement
        past_approved = self.env['hr.announcement'].create({
            'announcement_reason': 'Past Event',
            'is_announcement': True,
            'date_start': past_date - timedelta(days=5),
            'date_end': past_date,
            'state': 'approved',
        })

        # Expired rejected announcement (should NOT be updated to expired)
        past_rejected = self.env['hr.announcement'].create({
            'announcement_reason': 'Past Rejected Event',
            'is_announcement': True,
            'date_start': past_date - timedelta(days=5),
            'date_end': past_date,
            'state': 'rejected',
        })

        # Active future announcement
        future_approved = self.env['hr.announcement'].create({
            'announcement_reason': 'Future Event',
            'is_announcement': True,
            'date_start': self.today,
            'date_end': future_date,
            'state': 'approved',
        })

        # Trigger cron method
        self.env['hr.announcement'].get_expiry_state()

        self.assertEqual(past_approved.state, 'expired')
        self.assertEqual(past_rejected.state, 'rejected')
        self.assertEqual(future_approved.state, 'approved')

    def test_07_employee_count_general_announcement(self):
        """ Verify employee announcement count updates for general announcements. """
        initial_count_1 = self.employee_1.announcement_count
        initial_count_2 = self.employee_2.announcement_count

        announcement = self.env['hr.announcement'].create({
            'announcement_reason': 'Company Holiday Notice',
            'is_announcement': True,
            'date_start': self.today,
            'date_end': self.today + timedelta(days=5),
        })
        announcement.action_send()
        announcement.action_approve()

        self.employee_1._compute_announcement_count()
        self.employee_2._compute_announcement_count()

        self.assertEqual(self.employee_1.announcement_count, initial_count_1 + 1)
        self.assertEqual(self.employee_2.announcement_count, initial_count_2 + 1)

    def test_08_employee_count_targeted_announcements(self):
        """ Verify employee announcement count updates for employee, department, and job targets. """
        # Targeted to Employee 1 only
        ann_emp = self.env['hr.announcement'].create({
            'announcement_reason': 'Personal Milestone',
            'is_announcement': False,
            'announcement_type': 'employee',
            'employee_ids': [(4, self.employee_1.id)],
            'date_start': self.today,
            'date_end': self.today + timedelta(days=5),
        })
        ann_emp.action_send()
        ann_emp.action_approve()

        # Targeted to Employee 1's department
        ann_dept = self.env['hr.announcement'].create({
            'announcement_reason': 'R&D Sprint Review',
            'is_announcement': False,
            'announcement_type': 'department',
            'department_ids': [(4, self.department.id)],
            'date_start': self.today,
            'date_end': self.today + timedelta(days=5),
        })
        ann_dept.action_send()
        ann_dept.action_approve()

        # Targeted to Employee 1's job position
        ann_job = self.env['hr.announcement'].create({
            'announcement_reason': 'Engineering Architecture Sync',
            'is_announcement': False,
            'announcement_type': 'job_position',
            'position_ids': [(4, self.job_position.id)],
            'date_start': self.today,
            'date_end': self.today + timedelta(days=5),
        })
        ann_job.action_send()
        ann_job.action_approve()

        self.employee_1._compute_announcement_count()
        self.employee_2._compute_announcement_count()

        # Employee 1 matches all three targeted announcements
        self.assertGreaterEqual(self.employee_1.announcement_count, 3)

        # Non-approved announcements (e.g. draft) must not be counted
        draft_ann = self.env['hr.announcement'].create({
            'announcement_reason': 'Unpublished Draft Notice',
            'is_announcement': False,
            'announcement_type': 'employee',
            'employee_ids': [(4, self.employee_2.id)],
            'date_start': self.today,
            'date_end': self.today + timedelta(days=5),
        })
        self.assertEqual(draft_ann.state, 'draft')
        self.employee_2._compute_announcement_count()
        self.assertEqual(self.employee_2.announcement_count, 0)

    def test_09_employee_action_announcement_view(self):
        """ Test action_announcement_view for 0, 1, and multiple announcements. """
        fresh_emp = self.env['hr.employee'].create({'name': 'Charlie Intern'})

        # Case 1: 0 announcements -> returns False
        action_empty = fresh_emp.action_announcement_view()
        self.assertFalse(action_empty)

        # Case 2: Exactly 1 announcement -> opens form view directly
        ann_1 = self.env['hr.announcement'].create({
            'announcement_reason': 'Welcome Charlie',
            'is_announcement': False,
            'announcement_type': 'employee',
            'employee_ids': [(4, fresh_emp.id)],
            'date_start': self.today,
            'date_end': self.today + timedelta(days=5),
        })
        ann_1.action_send()
        ann_1.action_approve()

        fresh_emp._compute_announcement_count()
        self.assertEqual(fresh_emp.announcement_count, 1)

        action_single = fresh_emp.action_announcement_view()
        self.assertIsInstance(action_single, dict)
        self.assertEqual(action_single.get('res_model'), 'hr.announcement')
        self.assertEqual(action_single.get('view_mode'), 'form')
        self.assertEqual(action_single.get('res_id'), ann_1.id)

        # Case 3: Multiple announcements -> opens list view with domain
        ann_2 = self.env['hr.announcement'].create({
            'announcement_reason': 'Safety Drill Notice',
            'is_announcement': False,
            'announcement_type': 'employee',
            'employee_ids': [(4, fresh_emp.id)],
            'date_start': self.today,
            'date_end': self.today + timedelta(days=5),
        })
        ann_2.action_send()
        ann_2.action_approve()

        fresh_emp._compute_announcement_count()
        self.assertEqual(fresh_emp.announcement_count, 2)

        action_multi = fresh_emp.action_announcement_view()
        self.assertIsInstance(action_multi, dict)
        self.assertEqual(action_multi.get('res_model'), 'hr.announcement')
        domain = action_multi.get('domain', [])
        ids_in_domain = [t[2] for t in domain if len(t) == 3 and t[0] == 'id' and t[1] == 'in'][0]
        self.assertIn(ann_1.id, ids_in_domain)
        self.assertIn(ann_2.id, ids_in_domain)

    def test_10_attachments_and_content(self):
        """ Test attaching files and rich content to announcement. """
        attachment = self.env['ir.attachment'].create({
            'name': 'guidelines.pdf',
            'raw': b'Mock PDF file content for test',
        })
        announcement = self.env['hr.announcement'].create({
            'announcement_reason': 'Safety Guidelines',
            'announcement': '<p>Please read the attached safety policy.</p>',
            'attachment_ids': [(4, attachment.id)],
            'is_announcement': True,
        })
        self.assertIn(attachment, announcement.attachment_ids)
        self.assertIn('safety policy', announcement.announcement)
