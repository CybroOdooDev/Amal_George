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

from datetime import timedelta
from odoo import fields, models
from odoo.tools.translate import _


class HrPayslip(models.Model):
    """Inherits hr.payslip to compute worked days from employee shift schedules."""
    _inherit = 'hr.payslip'

    def _get_worked_day_lines(self, domain=None, check_out_of_version=True):
        """Override to compute worked day lines based on the employee's
        shift schedules instead of hr.contract (removed in Odoo 19)."""
        res = super()._get_worked_day_lines(domain=domain,
                                            check_out_of_version=check_out_of_version)
        employee = self.employee_id
        if not employee or not employee.shift_schedule_ids or not self.date_from or not self.date_to:
            return res

        schedules = employee.shift_schedule_ids.filtered(
            lambda s: s.start_date <= self.date_to and s.end_date >= self.date_from
        )
        if not schedules:
            return res

        def was_on_leave(emp_id, d_from, d_to):
            return self.env['hr.leave'].search([
                ('state', '=', 'validate'),
                ('employee_id', '=', emp_id),
                ('date_from', '<=', fields.Datetime.to_string(d_from)),
                ('date_to', '>=', fields.Datetime.to_string(d_to)),
            ], limit=1)

        attendance_type = self.env.ref(
            'hr_work_entry.work_entry_type_attendance',
            raise_if_not_found=False)
        if not attendance_type:
            attendance_type = self.env['hr.work.entry.type'].search(
                [('code', '=', 'WORK100')], limit=1)

        hours_per_day = (
            self._get_worked_day_lines_hours_per_day()
            if hasattr(self, '_get_worked_day_lines_hours_per_day') else 8.0)
        if not hours_per_day:
            hours_per_day = 8.0

        uom_day = self.env.ref('product.product_uom_day', raise_if_not_found=False)
        uom_hour = self.env.ref('product.product_uom_hour', raise_if_not_found=False)
        interval_data = []
        attendances = {
            'work_entry_type_id': attendance_type.id if attendance_type else False,
            'name': (attendance_type.name if attendance_type
                     else _("Normal Working Days paid at 100%")),
            'sequence': attendance_type.sequence if attendance_type else 1,
            'number_of_days': 0.0,
            'number_of_hours': 0.0,
        }
        leaves = {}

        for schedule in schedules:
            sched_start = max(schedule.start_date, self.date_from)
            sched_end = min(schedule.end_date, self.date_to)
            nb_days = (sched_end - sched_start).days + 1
            for day in range(nb_days):
                day_date = sched_start + timedelta(days=day)
                for interval in schedule.hr_shift_id._get_day_work_intervals(day_date):
                    interval_data.append(
                        (interval, was_on_leave(employee.id,
                                                interval[0], interval[1])))

        for interval, holiday in interval_data:
            hours = (interval[1] - interval[0]).total_seconds() / 3600.0
            if holiday:
                wet = (
                    holiday.holiday_status_id.work_entry_type_id
                    if hasattr(holiday.holiday_status_id, 'work_entry_type_id')
                    and holiday.holiday_status_id.work_entry_type_id else False)
                if not wet:
                    wet = self.env.ref('hr_work_entry.work_entry_type_leave',
                                       raise_if_not_found=False)
                leave_key = wet.id if wet else holiday.holiday_status_id.id
                if leave_key in leaves:
                    leaves[leave_key]['number_of_hours'] += hours
                else:
                    leaves[leave_key] = {
                        'work_entry_type_id': wet.id if wet else False,
                        'name': wet.name if wet else holiday.holiday_status_id.name,
                        'sequence': wet.sequence if wet else 5,
                        'number_of_days': 0.0,
                        'number_of_hours': hours,
                    }
            else:
                attendances['number_of_hours'] += hours

        leave_vals = list(leaves.values())
        for data in [attendances] + leave_vals:
            data['number_of_days'] = (
                uom_hour._compute_quantity(data['number_of_hours'], uom_day)
                if uom_day and uom_hour else round(data['number_of_hours'] / hours_per_day, 5))

        if attendance_type:
            res = [r for r in res if r.get('work_entry_type_id') != attendance_type.id]
        else:
            res = [r for r in res if r.get('code') != 'WORK100']

        if attendances.get('work_entry_type_id'):
            res.append(attendances)

        leave_entry_type_ids = {
            lv['work_entry_type_id'] for lv in leave_vals
            if lv.get('work_entry_type_id')
        }
        if leave_entry_type_ids:
            res = [r for r in res if r.get('work_entry_type_id') not in leave_entry_type_ids]
        for lv in leave_vals:
            if lv.get('work_entry_type_id'):
                res.append(lv)

        return sorted(res, key=lambda d: d.get('sequence', 10))