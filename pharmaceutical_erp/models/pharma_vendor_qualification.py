# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.translate import _


class PharmaVendorQualification(models.Model):
    """
    Vendor Qualification — records the qualification status, audit scores,
    and validity dates of pharmaceutical raw material / service vendors.
    """
    _name = 'pharma.vendor.qualification'
    _description = 'Vendor Qualification'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'audit_date desc, id desc'

    vendor_id = fields.Many2one(
        comodel_name='res.partner',
        string='Vendor',
        required=True,
        ondelete='restrict',
        index=True,
        tracking=True,
        help='Vendor going through the qualification process.'
    )

    product_id = fields.Many2one(
        comodel_name='product.template',
        string='Product',
        required=True,
        ondelete='restrict',
        index=True,
        tracking=True,
        help='Product they are being qualified to supply.'
    )

    status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('questionnaire_sent', 'Questionnaire Sent'),
            ('documents_received', 'Documents Received'),
            ('audit_scheduled', 'Audit Scheduled'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        help='Tracks where the vendor is in the qualification journey.'
    )

    audit_date = fields.Date(
        string='Audit Date',
        tracking=True,
        help='Date the physical or remote audit was conducted.'
    )

    audit_score = fields.Float(
        string='Audit Score',
        tracking=True,
        help='Score given to the vendor after the audit.'
    )

    gmp_certificate = fields.Binary(
        string='GMP Certificate',
        help="Vendor's GMP certificate uploaded as a file."
    )

    approved_by = fields.Many2one(
        comodel_name='res.users',
        string='Approved By',
        tracking=True,
        help='QA person who gave final approval.'
    )

    rejection_reason = fields.Text(
        string='Rejection Reason',
        help='Reason recorded if the vendor was rejected.'
    )

    avl_id = fields.Many2one(
        comodel_name='pharma.avl',
        string='AVL Entry',
        readonly=True,
        ondelete='set null',
        help='AVL entry auto-created when vendor is approved.'
    )

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    @api.depends('vendor_id', 'product_id', 'audit_date')
    def _compute_display_name(self):
        for record in self:
            vendor = record.vendor_id.name or _('New')
            product = record.product_id.name or ''
            date_str = f" ({record.audit_date})" if record.audit_date else ""
            record.display_name = f"QUAL / {vendor} - {product}{date_str}" if product else f"QUAL / {vendor}{date_str}"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.status == 'approved':
                rec.with_context(skip_avl_trigger=True)._create_or_update_avl()
        return records

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('skip_avl_trigger'):
            return res
        trigger_fields = {'status', 'audit_date', 'approved_by', 'vendor_id', 'product_id'}
        if trigger_fields.intersection(vals.keys()):
            for rec in self:
                if rec.status == 'approved':
                    rec.with_context(skip_avl_trigger=True)._create_or_update_avl()
        return res

    def _create_or_update_avl(self):
        self.ensure_one()
        if not self.vendor_id or not self.product_id:
            return

        # Check if an AVL record already exists
        avl = self.env['pharma.avl'].search([
            ('vendor_id', '=', self.vendor_id.id),
            ('product_id', '=', self.product_id.id)
        ], limit=1)

        vals = {
            'vendor_id': self.vendor_id.id,
            'product_id': self.product_id.id,
            'status': 'approved',
            'approval_date': self.audit_date or fields.Date.context_today(self),
            'approved_by': self.approved_by.id or self.env.uid,
        }

        if avl:
            avl.write(vals)
        else:
            avl = self.env['pharma.avl'].create(vals)

        if self.avl_id != avl:
            self.write({'avl_id': avl.id})

    def action_send_questionnaire(self):
        for rec in self:
            if rec.status == 'draft':
                rec.status = 'questionnaire_sent'

    def action_receive_documents(self):
        for rec in self:
            if rec.status == 'questionnaire_sent':
                rec.status = 'documents_received'

    def action_schedule_audit(self):
        for rec in self:
            if rec.status == 'documents_received':
                rec.status = 'audit_scheduled'

    def action_approve(self):
        for rec in self:
            if rec.status == 'audit_scheduled':
                rec.write({
                    'status': 'approved',
                    'approved_by': self.env.user.id,
                    'audit_date': rec.audit_date or fields.Date.context_today(self),
                })

    def action_reject(self):
        for rec in self:
            if rec.status == 'audit_scheduled':
                rec.status = 'rejected'

    def action_reset_draft(self):
        for rec in self:
            rec.status = 'draft'