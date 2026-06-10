# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.translate import _


class PharmaOosInvestigation(models.Model):
    """
    OOS Investigation — tracks investigations when QC results fall out of spec.
    """
    _name = 'pharma.oos.investigation'
    _description = 'OOS Investigation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(
        string='Investigation Number',
        required=True,
        copy=False,
        readonly=True,
        default='/'
    )

    result_line_id = fields.Many2one(
        comodel_name='pharma.qc.result.line',
        string='OOS Result Line',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
        help='The specific OOS result that triggered this investigation.'
    )

    phase = fields.Selection(
        selection=[
            ('phase_1', 'Phase I'),
            ('phase_2', 'Phase II'),
        ],
        string='Phase',
        default='phase_1',
        required=True,
        tracking=True,
        help='Phase I checks for lab error, Phase II checks the full batch.'
    )

    lab_error_found = fields.Boolean(
        string='Lab Error Found',
        default=False,
        tracking=True,
        help='If True in Phase I, result is invalidated and re-tested.'
    )

    conclusion = fields.Text(
        string='Conclusion',
        tracking=True,
        help='Final conclusion of the investigation.'
    )

    disposition = fields.Selection(
        selection=[
            ('release', 'Release'),
            ('reject', 'Reject'),
            ('rework', 'Rework'),
        ],
        string='Disposition',
        tracking=True,
        help='Final decision on the batch after investigation.'
    )

    investigated_by = fields.Many2one(
        comodel_name='res.users',
        string='Investigated By',
        tracking=True,
        help='QA person who led the investigation.'
    )

    closed_on = fields.Datetime(
        string='Closed On',
        tracking=True,
        help='Date and time the investigation was formally closed.'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('pharma.oos.investigation') or '/'
        return super().create(vals_list)
