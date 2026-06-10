# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.exceptions import ValidationError


class PharmaQcSpec(models.Model):
    """
    QC Specification — one record per product per testing stage.
    Holds parameter lines (acceptance criteria) used by QC test orders.
    Must be QA-approved before it can be linked to any test order.
    """
    _name = 'pharma.qc.spec'
    _description = 'QC Specification'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'product_id, stage'

    # ── Identity ─────────────────────────────────────────────────────────────
    name = fields.Char(
        string='Specification Name',
        required=True,
        copy=False,
        tracking=True,
    )

    product_id = fields.Many2one(
        comodel_name='product.template',
        string='Product',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
    )

    stage = fields.Selection(
        selection=[
            ('incoming', 'Incoming / Raw Material'),
            ('inprocess', 'In-Process (IPQC)'),
            ('finished', 'Finished Goods'),
            ('stability', 'Stability'),
        ],
        string='Testing Stage',
        required=True,
        tracking=True,
    )

    pharmacopoeial_ref = fields.Selection(
        selection=[
            ('bp', 'BP'),
            ('usp', 'USP'),
            ('ep', 'EP'),
            ('ip', 'IP'),
            ('inhouse', 'In-House'),
        ],
        string='Pharmacopoeial Reference',
        tracking=True,
    )

    version = fields.Char(
        string='Version',
        default='1.0',
        required=True,
        tracking=True,
    )

    # ── Status / Approval ────────────────────────────────────────────────────
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('review', 'Under Review'),
            ('approved', 'Approved'),
            ('obsolete', 'Obsolete'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )

    approved_by = fields.Many2one(
        comodel_name='res.users',
        string='Approved By',
        tracking=True,
    )

    approval_date = fields.Date(
        string='Approval Date',
        tracking=True,
    )

    effective_date = fields.Date(
        string='Effective Date',
        tracking=True,
        help='Date from which this specification version is active.',
    )

    # ── Parameter Lines ───────────────────────────────────────────────────────
    parameter_ids = fields.One2many(
        comodel_name='pharma.qc.spec.line',
        inverse_name='spec_id',
        string='Test Parameters',
    )

    notes = fields.Text(string='Notes / Sampling Instructions')

    # ── Constraints ───────────────────────────────────────────────────────────
    _sql_constraints = [
        (
            'unique_product_stage_version',
            'UNIQUE(product_id, stage, version)',
            'A specification with this version already exists for this product and stage.',
        ),
    ]

    @api.constrains('state', 'approved_by', 'approval_date')
    def _check_approval(self):
        for rec in self:
            if rec.state == 'approved' and not (rec.approved_by and rec.approval_date):
                raise ValidationError(
                    _('Approved By and Approval Date are required when approving a specification.')
                )

    # ── Actions ───────────────────────────────────────────────────────────────
    def action_submit_review(self):
        self.write({'state': 'review'})

    def action_approve(self):
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approval_date': fields.Date.today(),
        })

    def action_obsolete(self):
        self.write({'state': 'obsolete'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class PharmaQcSpecLine(models.Model):
    """
    A single test parameter within a QC specification.
    """
    _name = 'pharma.qc.spec.line'
    _description = 'QC Specification Parameter'
    _order = 'sequence, id'

    spec_id = fields.Many2one(
        comodel_name='pharma.qc.spec',
        string='Specification',
        required=True,
        ondelete='cascade',
        index=True,
    )

    sequence = fields.Integer(string='Seq.', default=10)

    parameter_name = fields.Char(
        string='Parameter',
        required=True,
        help='Name of the test parameter (e.g. Assay, Water Content, Hardness).',
    )

    test_method = fields.Char(
        string='Test Method',
        help='Method reference (e.g. HPLC, BP 2.9.1, In-house STP-QC-001).',
    )

    uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unit',
    )

    min_value = fields.Float(
        string='Min. Limit',
        digits=(16, 4),
        help='Minimum acceptable value (leave 0 if not applicable).',
    )

    max_value = fields.Float(
        string='Max. Limit',
        digits=(16, 4),
        help='Maximum acceptable value (leave 0 if not applicable).',
    )

    acceptance_criteria = fields.Char(
        string='Acceptance Criteria (Text)',
        help='Text-based criteria for qualitative parameters (e.g. "White crystalline powder").',
    )

    is_critical = fields.Boolean(
        string='Critical Parameter',
        default=False,
        help='Mark if this is a Critical Quality Attribute (CQA).',
    )

    notes = fields.Char(string='Remarks')
