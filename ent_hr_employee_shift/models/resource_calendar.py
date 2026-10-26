# -*- coding: utf-8 -*-
######################################################################################
#
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#    or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#    ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
########################################################################################
import datetime
from datetime import time, timedelta
import math
from collections import namedtuple
from pytz import timezone, utc
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round
from odoo.tools.translate import _


class ResourceCalendar(models.Model):
    """This is ued to inherit resource.calendar to add new functionalities"""
    _inherit = 'resource.calendar'

    def _get_default_attendance_ids(self):
        """This is used to return the attends of the employee"""
        return [
            (0, 0, {'name': _('Monday Morning'), 'dayofweek': '0',
                    'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Tuesday Morning'), 'dayofweek': '1',
                    'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Wednesday Morning'), 'dayofweek': '2',
                    'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Thursday Morning'), 'dayofweek': '3',
                    'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Friday Morning'), 'dayofweek': '4',
                    'hour_from': 8, 'hour_to': 12}),
        ]

    _interval_obj = namedtuple('Interval', ('start_datetime', 'end_datetime',
                                            'data'))

    color = fields.Integer(string='Color Index',
                           help="Color Index of Resource Calendar")
    hr_department_id = fields.Many2one('hr.department', string="Department",
                                       required=True,
                                       help="Department of Resource Calendar")
    sequence = fields.Integer(string="Sequence", required=True, default=1,
                              help="Sequence of Resource Calendar")
    attendance_ids = fields.One2many(
        'resource.calendar.attendance', 'calendar_id', 'Workings Time',
        copy=True, default=_get_default_attendance_ids,
        help="Attendance ID's of Resource Calendar")

    def string_to_datetime(self, value):
        """ Convert the given string value to a datetime in UTC. """
        dt = fields.Datetime.to_datetime(value)
        if not dt:
            return False
        if dt.tzinfo:
            return dt.astimezone(utc)
        tz = timezone(self.tz) if self.tz else utc
        return tz.localize(dt).astimezone(utc)

    def float_to_time(self, hours):
        """ Convert a number of hours into a time object. """
        if hours == 24.0:
            return time.max
        fractional, integral = math.modf(hours)
        return time(int(integral), int(float_round(60 * fractional,
                                                   precision_digits=0)), 0)

    def _interval_new(self, start_datetime, end_datetime, kw=None):
        """Get new interval"""
        kw = kw if kw is not None else dict()
        kw.setdefault('attendances', self.env['resource.calendar.attendance'])
        kw.setdefault('leaves', self.env['resource.calendar.leaves'])
        return self._interval_obj(start_datetime, end_datetime, kw)

    def _get_day_work_intervals(self,
                                day_date,
                                start_time=None,
                                end_time=None,
                                compute_leaves=False,
                                resource_id=None):
        "Gets day work intervals"
        self.ensure_one()
        day_date_val = day_date.date() if isinstance(day_date, datetime.datetime) else day_date
        if not start_time:
            start_time = time.min
        if not end_time:
            end_time = time.max
        working_intervals = [att_interval for att_interval in
                             self._iter_day_attendance_intervals(day_date_val,
                                                                 start_time,
                                                                 end_time)]
        # filter according to leaves
        if compute_leaves:
            if hasattr(self, '_get_leave_intervals'):
                leaves = self._get_leave_intervals(
                    resource_id=resource_id,
                    start_datetime=datetime.datetime.combine(day_date_val, start_time),
                    end_datetime=datetime.datetime.combine(day_date_val, end_time))
                working_intervals = [
                    sub_interval
                    for interval in working_intervals
                    for sub_interval in self._leave_intervals(interval, leaves)]
        # adapt tz
        return [self._interval_new(
            self.string_to_datetime(interval[0]),
            self.string_to_datetime(interval[1]),
            interval[2]) for interval in working_intervals]

    def _get_day_attendances(self, day_date, start_time, end_time):
        """ Given a day date, return matching attendances. Those can be limited
        by starting and ending time objects. """
        self.ensure_one()
        day_date_val = day_date.date() if isinstance(day_date, datetime.datetime) else day_date
        weekday = day_date_val.weekday()
        week_type = str(self.env['resource.calendar.attendance'].get_week_type(day_date_val)) if hasattr(self.env['resource.calendar.attendance'], 'get_week_type') else False
        attendances = self.env['resource.calendar.attendance']

        for attendance in self.attendance_ids:
            if attendance.display_type:
                continue
            if attendance.day_period == 'lunch':
                continue
            if int(attendance.dayofweek) != weekday:
                continue
            if self.two_weeks_calendar and week_type and attendance.week_type and attendance.week_type != week_type:
                continue
            if 'date_from' in attendance._fields and attendance.date_from:
                att_date_from = fields.Date.to_date(attendance.date_from)
                if att_date_from and att_date_from > day_date_val:
                    continue
            if 'date_to' in attendance._fields and attendance.date_to:
                att_date_to = fields.Date.to_date(attendance.date_to)
                if att_date_to and att_date_to < day_date_val:
                    continue
            if start_time and self.float_to_time(attendance.hour_to) < start_time:
                continue
            if end_time and self.float_to_time(attendance.hour_from) > end_time:
                continue
            attendances |= attendance
        return attendances

    def _iter_day_attendance_intervals(self, day_date, start_time, end_time):
        """ Get an iterator of all interval of current day attendances. """
        day_date_val = day_date.date() if isinstance(day_date, datetime.datetime) else day_date
        for calendar_working_day in self._get_day_attendances(day_date_val,
                                                              start_time,
                                                              end_time):
            from_time = self.float_to_time(calendar_working_day.hour_from)
            to_time = self.float_to_time(calendar_working_day.hour_to)

            dt_f = datetime.datetime.combine(day_date_val, max(from_time,
                                                               start_time))
            dt_t = datetime.datetime.combine(day_date_val, min(to_time,
                                                               end_time))

            yield self._interval_new(dt_f, dt_t, {'attendances': calendar_working_day})

    @api.constrains('sequence')
    def validate_seq(self):
        """Validate the sequence"""
        if self.hr_department_id.id:
            record = self.search(
                [('hr_department_id', '=', self.hr_department_id.id),
                 ('sequence', '=', self.sequence),
                 ('company_id', '=', self.company_id.id)])
            if len(record) > 1:
                raise ValidationError("One record with same sequence is "
                                      "already active. You can't activate "
                                      "more than one record  at a time")
