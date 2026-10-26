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

from odoo import fields, models


class HrShiftGenerate(models.TransientModel):
    """Creates the model hr.shift.generate"""
    _name = 'hr.shift.generate'
    _description = 'Generates a shift'

    hr_department_id = fields.Many2one('hr.department', string='Department',
                                       help='Department of Shift Generate')
    start_date = fields.Date(string='Start Date', required=True,
                             help='Start date of shift generation')
    end_date = fields.Date(string='End Date', required=True,
                           help='End date of shift generation')
    company_id = fields.Many2one('res.company', string='Company', help='Company')

    def _get_next_shift(self, current_shift, department_id):
        """Return the next shift in sequence for a department.
        Rotates back to sequence 1 if no higher sequence exists."""
        seq_no = (current_shift.sequence + 1) if current_shift else 1
        new_shift = self.env['resource.calendar'].search([
            ('sequence', '=', seq_no),
            ('hr_department_id', '=', department_id)], limit=1)
        if not new_shift:
            new_shift = self.env['resource.calendar'].search([
                ('sequence', '=', 1),
                ('hr_department_id', '=', department_id)], limit=1)
        if not new_shift:
            dept = self.env['hr.department'].browse(department_id)
            new_shift = self.env['resource.calendar'].create({
                'name': dept.name + ' Shift',
                'hr_department_id': department_id,
                'sequence': 1,
                'company_id': self.env.company.id,
            })
        return new_shift

    def action_schedule_shift(self):
        """Create mass schedule for all departments (or a specific one)
        based on the shift scheduled in the corresponding employee."""
        domain = []
        if self.hr_department_id:
            domain = [('department_id', '=', self.hr_department_id.id)]
        for employee in self.env['hr.employee'].search(domain):
            if not employee.department_id:
                continue
            current_shift = False
            if employee.shift_schedule_ids:
                last = employee.shift_schedule_ids[-1]
                current_shift = self.env['resource.calendar'].search([
                    ('hr_department_id', '=', employee.department_id.id),
                    ('name', '=', last.hr_shift_id.name)], limit=1)
            new_shift = self._get_next_shift(current_shift,
                                             employee.department_id.id)
            if new_shift:
                employee.shift_schedule_ids = [(0, 0, {
                    'hr_shift_id': new_shift.id,
                    'start_date': self.start_date,
                    'end_date': self.end_date,
                })]