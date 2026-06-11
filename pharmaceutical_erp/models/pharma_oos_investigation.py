# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.exceptions import ValidationError



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

    test_order_id = fields.Many2one(
        comodel_name='pharma.qc.test.order',
        string='Test Order',
        related='result_line_id.test_order_id',
        store=True
    )

    def action_view_test_order(self):
        self.ensure_one()
        if self.test_order_id:
            return {
                'name': 'QC Test Order',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'pharma.qc.test.order',
                'res_id': self.test_order_id.id,
            }

    def action_escalate_to_phase_2(self):
        for rec in self:
            if rec.closed_on:
                raise ValidationError(_("Closed investigations cannot be escalated."))
            if rec.phase != 'phase_1':
                raise ValidationError(_("Only Phase I investigations can be escalated."))
            if rec.lab_error_found:
                raise ValidationError(_("Cannot escalate to Phase II if a lab error was found. Please invalidate and re-test instead."))
            rec.phase = 'phase_2'

    def action_invalidate_retest(self):
        for rec in self:
            if rec.closed_on:
                raise ValidationError(_("This investigation is already closed."))
            if rec.phase != 'phase_1':
                raise ValidationError(_("Invalidation and re-testing can only be triggered in Phase I."))
            if not rec.lab_error_found:
                raise ValidationError(_("You must select 'Lab Error Found' to invalidate and re-test."))
            
            # Invalidate results: reset actual_value to 0.0 and result_entered to False
            rec.result_line_id.write({
                'actual_value': 0.0,
                'result_entered': False,
            })
            
            # Set test order status to in_progress (if under_investigation)
            test_order = rec.result_line_id.test_order_id
            if test_order.status == 'under_investigation':
                # Check if there are other open investigations for this test order
                other_open = self.env['pharma.oos.investigation'].search([
                    ('result_line_id.test_order_id', '=', test_order.id),
                    ('id', '!=', rec.id),
                    ('closed_on', '=', False)
                ])
                if not other_open:
                    test_order.write({'status': 'in_progress'})

            rec.write({
                'investigated_by': self.env.user.id,
                'closed_on': fields.Datetime.now()
            })

    def action_close_investigation(self):
        for rec in self:
            if rec.closed_on:
                raise ValidationError(_("This investigation is already closed."))
            if rec.phase != 'phase_2':
                raise ValidationError(_("Only Phase II investigations can be closed directly. If Phase I is sufficient, select lab error found or escalate to Phase II."))
            if not rec.conclusion:
                raise ValidationError(_("You must enter a conclusion before closing Phase II."))
            if not rec.disposition:
                raise ValidationError(_("You must enter a disposition before closing Phase II."))
            
            rec.write({
                'investigated_by': self.env.user.id,
                'closed_on': fields.Datetime.now()
            })
            
            # Update parent test order status
            test_order = rec.result_line_id.test_order_id
            if test_order:
                # If disposition is reject or rework, set test order to failed
                if rec.disposition in ('reject', 'rework'):
                    test_order.write({'status': 'failed'})
                elif rec.disposition == 'release':
                    # Check if all other OOS investigations for this test order are closed
                    other_open = self.env['pharma.oos.investigation'].search([
                        ('result_line_id.test_order_id', '=', test_order.id),
                        ('id', '!=', rec.id),
                        ('closed_on', '=', False)
                    ])
                    if not other_open:
                        # Also check if any closed investigations were rejected/reworked
                        other_failed = self.env['pharma.oos.investigation'].search([
                            ('result_line_id.test_order_id', '=', test_order.id),
                            ('id', '!=', rec.id),
                            ('disposition', 'in', ('reject', 'rework')),
                            ('lab_error_found', '=', False)
                        ])
                        if other_failed:
                            test_order.write({'status': 'failed'})
                        else:
                            # Set back to in_progress so reviewer can sign off
                            test_order.write({'status': 'in_progress'})

    @api.constrains('closed_on', 'disposition')
    def _check_close(self):
        """Bug 7: enforce that a disposition is always recorded when an
        investigation is closed, so the record is never in a half-closed state."""
        for rec in self:
            if rec.closed_on and not rec.disposition:
                # Phase I lab-error closures (action_invalidate_retest) do not
                # require a disposition — only Phase II closures do.  Allow the
                # Phase I path through so that invalidate_retest can close without
                # forcing the user to pick a disposition.
                if rec.phase == 'phase_2':
                    raise ValidationError(
                        _("A Phase II investigation must have a disposition before it can be closed.")
                    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('pharma.oos.investigation') or '/'
        return super().create(vals_list)

    def write(self, vals):
        for rec in self:
            if rec.closed_on:
                restricted_fields = ('result_line_id', 'lab_error_found', 'phase', 'conclusion', 'disposition')
                if any(f in vals for f in restricted_fields):
                    raise ValidationError(_("Cannot modify details of a closed OOS investigation."))
        return super().write(vals)
