# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.exceptions import ValidationError


class PharmaQcTestOrder(models.Model):
    """
    QC Test Order — records quality control testing orders, stage, spec,
    lot information, and results.
    """
    _name = 'pharma.qc.test.order'
    _description = 'QC Test Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(
        string='Test Order Number',
        required=True,
        copy=False,
        readonly=True,
        default='/'
    )

    lot_id = fields.Many2one(
        comodel_name='stock.lot',
        string='Lot',
        required=True,
        ondelete='restrict',
        index=True,
        tracking=True,
        help='Which material or product lot is being tested.'
    )

    product_id = fields.Many2one(
        comodel_name='product.template',
        string='Product',
        required=True,
        ondelete='restrict',
        index=True,
        tracking=True,
        help='Product linked to this test order.'
    )

    spec_id = fields.Many2one(
        comodel_name='pharma.qc.spec',
        string='Specification',
            ondelete='restrict',
        index=True,
        tracking=True,
        help='QC specification auto-loaded based on product and stage.'
    )

    stage = fields.Selection(
        selection=[
            ('incoming', 'Incoming'),
            ('inprocess', 'In-Process'),
            ('finished', 'Finished Goods'),
        ],
        string='Testing Stage',
        required=True,
        default='incoming',
        tracking=True,
        help='QC checkpoint stage.'
    )

    status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('under_investigation', 'Under Investigation'),
            ('passed', 'Passed'),
            ('failed', 'Failed'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        help='Overall status of the test order.'
    )

    entered_by = fields.Many2one(
        comodel_name='res.users',
        string='Analyst',
        tracking=True,
        help='Analyst who entered the results.'
    )

    reviewed_by = fields.Many2one(
        comodel_name='res.users',
        string='Reviewed By',
        tracking=True,
        help='Second person who reviewed and signed, must differ from analyst.'
    )

    result_line_ids = fields.One2many(
        comodel_name='pharma.qc.result.line',
        inverse_name='test_order_id',
        string='Test Results',
        copy=True
    )

    @api.constrains('entered_by', 'reviewed_by')
    def _check_reviewer(self):
        for rec in self:
            if rec.entered_by and rec.reviewed_by and rec.entered_by == rec.reviewed_by:
                raise ValidationError(_("The reviewer must be a different person than the analyst who entered the results."))

    @api.onchange('product_id', 'stage')
    def _onchange_product_stage(self):
        if self.product_id and self.stage:
            spec = self.env['pharma.qc.spec'].search([
                ('product_id', '=', self.product_id.id),
                ('stage', '=', self.stage),
                ('state', '=', 'approved')
            ], order='version desc', limit=1)
            if spec:
                self.spec_id = spec.id
            else:
                self.spec_id = False
        else:
            self.spec_id = False

    @api.onchange('spec_id')
    def _onchange_spec_id(self):
        if self.spec_id:
            # Clear old lines
            self.result_line_ids = [(5, 0, 0)]
            # Create new lines from spec parameter lines
            lines = []
            for line in self.spec_id.parameter_ids:
                lines.append((0, 0, {
                    'parameter': line.parameter_name,
                    'expected_min': line.min_value,
                    'expected_max': line.max_value,
                    'uom': line.uom_id.name or '',
                    'actual_value': 0.0,
                }))
            self.result_line_ids = lines

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('pharma.qc.test.order') or '/'

            # Auto load spec_id if product and stage are provided but spec_id is not
            if not vals.get('spec_id') and vals.get('product_id') and vals.get('stage'):
                spec = self.env['pharma.qc.spec'].search([
                    ('product_id', '=', vals['product_id']),
                    ('stage', '=', vals['stage']),
                    ('state', '=', 'approved')
                ], order='version desc', limit=1)
                if spec:
                    vals['spec_id'] = spec.id

            # If spec_id is set/found, auto-load parameters if lines not provided
            if vals.get('spec_id') and not vals.get('result_line_ids'):
                spec = self.env['pharma.qc.spec'].browse(vals['spec_id'])
                lines = []
                for line in spec.parameter_ids:
                    lines.append((0, 0, {
                        'parameter': line.parameter_name,
                        'expected_min': line.min_value,
                        'expected_max': line.max_value,
                        'uom': line.uom_id.name or '',
                        'actual_value': 0.0,
                    }))
                vals['result_line_ids'] = lines
        return super().create(vals_list)


class PharmaQcResultLine(models.Model):
    """
    QC Result Line — records the actual testing values for each parameter.
    """
    _name = 'pharma.qc.result.line'
    _description = 'QC Result Line'

    test_order_id = fields.Many2one(
        comodel_name='pharma.qc.test.order',
        string='Test Order',
        required=True,
        ondelete='cascade',
        index=True
    )

    parameter = fields.Char(
        string='Parameter',
        required=True,
        help='Test parameter name copied from spec.'
    )

    expected_min = fields.Float(
        string='Expected Min',
        help='Minimum copied from spec for reference during entry.'
    )

    expected_max = fields.Float(
        string='Expected Max',
        help='Maximum copied from spec for reference during entry.'
    )

    actual_value = fields.Float(
        string='Actual Value',
        help='Result entered by the analyst after running the test.'
    )

    uom = fields.Char(
        string='UoM',
        help='Unit of measurement for this result.'
    )

    is_oos = fields.Boolean(
        string='OOS',
        compute='_compute_status',
        store=True,
        help='Auto set to True if actual value falls outside min/max.'
    )

    status = fields.Selection(
        selection=[
            ('pass', 'Pass'),
            ('fail', 'Fail'),
            ('oos', 'OOS'),
        ],
        string='Status',
        compute='_compute_status',
        store=True,
        help='Computed based on actual vs expected range.'
    )

    @api.depends('actual_value', 'expected_min', 'expected_max')
    def _compute_status(self):
        for rec in self:
            is_oos = False
            if rec.expected_min and rec.actual_value < rec.expected_min:
                is_oos = True
            if rec.expected_max and rec.actual_value > rec.expected_max:
                is_oos = True
            rec.is_oos = is_oos
            rec.status = 'oos' if is_oos else 'pass'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.is_oos:
                rec._create_oos_investigation()
        return records

    def write(self, vals):
        pre_oos = {rec.id: rec.is_oos for rec in self}
        res = super().write(vals)
        for rec in self:
            if rec.is_oos and not pre_oos.get(rec.id):
                existing = self.env['pharma.oos.investigation'].search([('result_line_id', '=', rec.id)], limit=1)
                if not existing:
                    rec._create_oos_investigation()
        return res

    def _create_oos_investigation(self):
        self.ensure_one()
        self.env['pharma.oos.investigation'].create({
            'result_line_id': self.id,
            'phase': 'phase_1',
        })
