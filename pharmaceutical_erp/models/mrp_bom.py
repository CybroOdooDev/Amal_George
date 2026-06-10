# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.exceptions import ValidationError


class MrpBom(models.Model):
    """
    Extends the standard Bill of Materials (Formula) with pharma-specific
    versioning, pharmacopoeial reference, and QA approval workflow.
    Only Approved formulas may be used to create production orders.
    """
    _inherit = 'mrp.bom'

    # ── Pharma Formula Fields ─────────────────────────────────────────────────
    formula_version = fields.Char(
        string='Formula Version',
        copy=False,
        tracking=True,
        help='Version identifier for this formula (e.g. v1.0, v2.1). '
             'Increment when ingredients or quantities change.',
    )

    formula_status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('approved', 'Approved'),
            ('obsolete', 'Obsolete'),
        ],
        string='Formula Status',
        default='draft',
        required=True,
        tracking=True,
        help='Only Approved formulas can be used to start a production order.',
    )

    pharmacopoeial_ref = fields.Selection(
        selection=[
            ('bp', 'BP (British Pharmacopoeia)'),
            ('usp', 'USP (United States Pharmacopeia)'),
            ('ep', 'EP (European Pharmacopoeia)'),
            ('ip', 'IP (Indian Pharmacopoeia)'),
            ('inhouse', 'In-House Specification'),
        ],
        string='Pharmacopoeial Reference',
        tracking=True,
        help='Standard this formula is written against.',
    )

    # ── Approval Fields ───────────────────────────────────────────────────────
    approved_by = fields.Many2one(
        comodel_name='res.users',
        string='Approved By',
        copy=False,
        tracking=True,
        help='QA person who signed off on this formula.',
    )

    approval_date = fields.Date(
        string='Approval Date',
        copy=False,
        tracking=True,
        help='Date the formula was approved for production use.',
    )

    # ── Theoretical Yield ────────────────────────────────────────────────────
    theoretical_yield = fields.Float(
        string='Theoretical Yield (%)',
        digits=(5, 2),
        default=100.0,
        tracking=True,
        help='Expected batch yield percentage. Values below the configured '
             'threshold trigger a QA investigation.',
    )

    # ── Change Control Reference ──────────────────────────────────────────────
    change_ref = fields.Char(
        string='Change Control Ref.',
        copy=False,
        tracking=True,
        help='Reference to the Change Control record that authorised this formula version.',
    )

    notes = fields.Text(string='Formula Notes / Manufacturing Instructions')

    # ── Constraints ───────────────────────────────────────────────────────────
    @api.constrains('formula_status', 'approved_by', 'approval_date')
    def _check_approval_fields(self):
        for rec in self:
            if rec.formula_status == 'approved' and not (rec.approved_by and rec.approval_date):
                raise ValidationError(
                    _('Approved By and Approval Date are required when setting formula status to Approved.')
                )

    # ── Actions ───────────────────────────────────────────────────────────────
    def action_approve_formula(self):
        for rec in self:
            rec.write({
                'formula_status': 'approved',
                'approved_by': self.env.user.id,
                'approval_date': fields.Date.today(),
            })

    def action_obsolete_formula(self):
        self.write({'formula_status': 'obsolete'})

    def action_reset_draft(self):
        self.write({
            'formula_status': 'draft',
            'approved_by': False,
            'approval_date': False,
        })
