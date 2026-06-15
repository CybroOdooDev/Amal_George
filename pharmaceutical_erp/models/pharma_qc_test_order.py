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

    oos_investigation_count = fields.Integer(
        string='OOS Investigations',
        compute='_compute_oos_investigation_count'
    )

    def _compute_oos_investigation_count(self):
        for order in self:
            order.oos_investigation_count = self.env['pharma.oos.investigation'].search_count([
                ('result_line_id.test_order_id', '=', order.id)
            ])

    def action_view_oos_investigations(self):
        self.ensure_one()
        return {
            'name': 'OOS Investigations',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'pharma.oos.investigation',
            'domain': [('result_line_id.test_order_id', '=', self.id)],
            'context': {},
        }

    def action_start_test(self):
        for rec in self:
            if rec.status != 'draft':
                raise ValidationError(_("Only draft test orders can be started."))
            vals = {'status': 'in_progress'}
            if not rec.entered_by:
                vals['entered_by'] = self.env.user.id
            rec.write(vals)

    def action_approve(self):
        for rec in self:
            if rec.status not in ('in_progress', 'under_investigation'):
                raise ValidationError(_("Only test orders in 'In Progress' or 'Under Investigation' status can be approved."))
            if rec.entered_by and rec.entered_by == self.env.user:
                raise ValidationError(_("The reviewer must be a different person than the analyst who entered the results."))

            # Check OOS investigations — all must be closed before approving
            investigations = self.env['pharma.oos.investigation'].search([
                ('result_line_id', 'in', rec.result_line_ids.ids)
            ])
            if any(not inv.closed_on for inv in investigations):
                raise ValidationError(_("Cannot approve a test order with open OOS investigations."))

            for line in rec.result_line_ids:
                if line.is_oos:
                    line_invs = sorted(
                        investigations.filtered(lambda i, l=line: i.result_line_id == l),
                        key=lambda i: i.id,
                    )
                    if not line_invs:
                        raise ValidationError(_("OOS result has no investigation record. Cannot approve."))
                    latest = line_invs[-1]
                    if not latest.lab_error_found and latest.disposition != 'release':
                        raise ValidationError(_("Cannot approve: OOS result has no 'Release' disposition and was not resolved as a lab error."))

            rec.write({
                'reviewed_by': self.env.user.id,
                'status': 'passed',
            })

    def action_reject(self):
        for rec in self:
            if rec.status not in ('in_progress', 'under_investigation'):
                raise ValidationError(_("Only test orders in 'In Progress' or 'Under Investigation' status can be rejected."))
            if rec.entered_by and rec.entered_by == self.env.user:
                raise ValidationError(_("The reviewer must be a different person than the analyst who entered the results."))
            rec.write({
                'reviewed_by': self.env.user.id,
                'status': 'failed',
            })

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
                    'has_min': line.min_value != 0.0 or getattr(line, 'has_min', True),
                    'expected_max': line.max_value,
                    'has_max': line.max_value != 0.0 or getattr(line, 'has_max', True),
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
                        'has_min': line.min_value != 0.0 or getattr(line, 'has_min', True),
                        'expected_max': line.max_value,
                        'has_max': line.max_value != 0.0 or getattr(line, 'has_max', True),
                        'uom': line.uom_id.name or '',
                        'actual_value': 0.0,
                    }))
                vals['result_line_ids'] = lines
        return super().create(vals_list)

    def write(self, vals):
        _many2one = {'product_id', 'lot_id', 'spec_id'}
        _selection = {'stage'}
        locked = _many2one | _selection
        for rec in self:
            if rec.status != 'draft':
                for field in locked:
                    if field not in vals:
                        continue
                    current = rec[field].id if field in _many2one else rec[field]
                    if vals[field] != current:
                        raise ValidationError(
                            _("Cannot modify material or parameter details once the test has started.")
                        )
        # If spec_id is updated on draft test orders and result_line_ids is not passed,
        # regenerate the result lines.
        if 'spec_id' in vals and not vals.get('result_line_ids'):
            spec = self.env['pharma.qc.spec'].browse(vals['spec_id']) if vals['spec_id'] else False
            lines = [(5, 0, 0)]
            if spec:
                for line in spec.parameter_ids:
                    lines.append((0, 0, {
                        'parameter': line.parameter_name,
                        'expected_min': line.min_value,
                        'has_min': line.min_value != 0.0 or getattr(line, 'has_min', True),
                        'expected_max': line.max_value,
                        'has_max': line.max_value != 0.0 or getattr(line, 'has_max', True),
                        'uom': line.uom_id.name or '',
                        'actual_value': 0.0,
                    }))
            vals['result_line_ids'] = lines

        res = super().write(vals)
        if 'status' in vals and vals['status'] == 'passed':
            for rec in self:
                if rec.lot_id:
                    rec.lot_id.action_approve_lot()
        return res


class PharmaQcResultLine(models.Model):
    """
    QC Result Line — records the actual testing values for each parameter.
    """
    _name = 'pharma.qc.result.line'
    _description = 'QC Result Line'
    _rec_name = 'parameter'

    test_order_id = fields.Many2one(
        comodel_name='pharma.qc.test.order',
        string='Test Order',
        required=True,
        ondelete='cascade',
        index=True
    )

    parameter = fields.Char(
        string='Parameter',
        help='Test parameter name copied from spec.'
    )

    expected_min = fields.Float(
        string='Expected Min',
        digits=(16, 4),
        help='Minimum copied from spec for reference during entry.',
        store=True
    )

    has_min = fields.Boolean(
        string='Has Min Limit',
        default=True,
        help='When True the expected_min is enforced, even if it is 0.0. '
             'Set to False for parameters that have no lower bound.'
    )

    expected_max = fields.Float(
        string='Expected Max',
        digits=(16, 4),
        help='Maximum copied from spec for reference during entry.',
        store=True
    )

    has_max = fields.Boolean(
        string='Has Max Limit',
        default=True,
        help='When True the expected_max is enforced, even if it is 0.0. '
             'Set to False for parameters that have no upper bound.'
    )

    actual_value = fields.Float(
        string='Actual Value',
        digits=(16, 4),
        help='Result entered by the analyst after running the test.'
    )

    uom = fields.Char(
        string='UoM',
        help='Unit of measurement for this result.'
    )

    result_entered = fields.Boolean(
        string='Result Entered',
        default=False,
        help='Indicates if the actual test result has been entered.'
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
            ('oos', 'OOS'),
        ],
        string='Result Status',
        compute='_compute_status',
        store=True,
        help='Pass — value within the accepted min/max range (or not yet entered). OOS — value entered and outside the accepted limits.',
        default=False,
    )

    @api.depends(
        'actual_value', 'expected_min', 'has_min',
        'expected_max', 'has_max', 'result_entered',
    )
    def _compute_status(self):
        for rec in self:
            is_oos = False
            if rec.result_entered:
                if rec.has_min and rec.actual_value < rec.expected_min:
                    is_oos = True
                if rec.has_max and rec.actual_value > rec.expected_max:
                    is_oos = True
            rec.is_oos = is_oos
            rec.status = 'oos' if is_oos else 'pass'

    @api.onchange('actual_value')
    def _onchange_actual_value(self):
        self.result_entered = True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'actual_value' in vals and vals.get('actual_value') != 0.0:
                vals['result_entered'] = True
        records = super().create(vals_list)
        for rec in records:
            if rec.is_oos:
                rec._create_oos_investigation()
        return records

    def write(self, vals):
        if 'actual_value' in vals and 'result_entered' not in vals:
            vals['result_entered'] = True
        _is_invalidation_reset = (
            vals.get('actual_value') == 0.0
            and vals.get('result_entered') is False
        )
        if 'actual_value' in vals and not _is_invalidation_reset:
            for rec in self:
                if rec.test_order_id.status not in ('draft', 'in_progress'):
                    raise ValidationError(
                        _('Results cannot be modified because the test order is not in progress.')
                    )
        pre_oos = {rec.id: rec.is_oos for rec in self}
        res = super().write(vals)
        for rec in self:
            if rec.is_oos and not pre_oos.get(rec.id):
                existing = self.env['pharma.oos.investigation'].search([
                    ('result_line_id', '=', rec.id),
                    ('closed_on', '=', False)
                ], limit=1)
                if not existing:
                    rec._create_oos_investigation()
        return res

    def _create_oos_investigation(self):
        self.ensure_one()
        self.env['pharma.oos.investigation'].create({
            'result_line_id': self.id,
            'phase': 'phase_1',
        })

        if self.test_order_id and self.test_order_id.status != 'under_investigation':
            self.test_order_id.write({'status': 'under_investigation'})


