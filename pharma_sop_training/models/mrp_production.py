# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <https://www.gnu.org/licenses/>.
#
#############################################################################

from odoo import fields, models


class MrpRoutingWorkcenter(models.Model):
    """Links a routing operation to the approved SOP describing how it runs."""
    _inherit = 'mrp.routing.workcenter'

    sop_id = fields.Many2one(
        comodel_name='pharma.sop',
        string='Linked SOP',
        domain="[('status', '=', 'effective')]",
        help='Approved SOP detailing how this routing operation must be executed. '
             'Required on every operation before its formula can be approved '
             '(enforced by the pharma formula approval constraint).',
    )


class MrpProduction(models.Model):
    """Backfills the operation SOP onto each generated BMR step."""
    _inherit = 'mrp.production'

    def action_create_bmr(self):
        """Executes the action_create_bmr operation."""
        res = super().action_create_bmr()
        for production in self:
            if not production.bom_id or not production.bom_id.operation_ids:
                continue
            bmr = production.bmr_ids[:1]
            if not bmr:
                continue
            for step in bmr.step_ids:
                operation = production.bom_id.operation_ids.filtered(
                    lambda op: op.sequence == step.sequence
                    and op.name == step.description
                )[:1]
                if operation and operation.sop_id:
                    step.sop_id = operation.sop_id.id
        return res
