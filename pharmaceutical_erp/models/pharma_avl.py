# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.exceptions import ValidationError


class PharmaAVL(models.Model):
    """
    Approved Vendor List (AVL) — one record per product-vendor pair.
    Only vendors with status 'approved' may be selected on a Purchase Order
    for the linked product.
    """
    _name = 'pharma.avl'
    _description = 'Approved Vendor List'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'product_id, status, vendor_id'

    # ── Core Fields ──────────────────────────────────────────────────────────
    product_id = fields.Many2one(
        comodel_name='product.template',
        string='Product',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
    )

    vendor_id = fields.Many2one(
        comodel_name='res.partner',
        string='Vendor',
        required=True,
        domain=[('supplier_rank', '>', 0)],
        ondelete='restrict',
        index=True,
        tracking=True,
    )

    status = fields.Selection(
        selection=[
            ('approved', 'Approved'),
            ('under_review', 'Under Review'),
            ('blocked', 'Blocked'),
        ],
        string='Status',
        default='under_review',
        required=True,
        tracking=True,
    )

    # ── Approval Info ────────────────────────────────────────────────────────
    approval_date = fields.Date(
        string='Approval Date',
        tracking=True,
        help='Date the vendor was approved for this product.',
    )

    approved_by = fields.Many2one(
        comodel_name='res.users',
        string='Approved By',
        tracking=True,
        help='QA person who approved this vendor.',
    )

    expiry_date = fields.Date(
        string='Approval Expiry Date',
        tracking=True,
        help='Date the vendor approval expires and must be re-evaluated.',
    )

    # ── Supporting Info ──────────────────────────────────────────────────────
    vendor_item_code = fields.Char(
        string="Vendor's Item Code",
        help="Vendor's own part number or code for this material.",
    )

    lead_time_days = fields.Integer(
        string='Lead Time (Days)',
        help='Typical delivery lead time in calendar days.',
    )

    notes = fields.Text(
        string='Notes',
        help='Any additional qualification remarks or special conditions.',
    )

    # ── Display Name ─────────────────────────────────────────────────────────
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
    )

    @api.depends('product_id', 'vendor_id')
    def _compute_display_name(self):
        for rec in self:
            product = rec.product_id.name or ''
            vendor = rec.vendor_id.name or ''
            rec.display_name = f'{product} / {vendor}' if product or vendor else _('New AVL')

    # ── Constraints ───────────────────────────────────────────────────────────
    _sql_constraints = [
        (
            'unique_product_vendor',
            'UNIQUE(product_id, vendor_id)',
            'A vendor can appear only once per product in the Approved Vendor List.',
        ),
    ]

    @api.constrains('status', 'approval_date', 'approved_by')
    def _check_approval_fields(self):
        for rec in self:
            if rec.status == 'approved' and not (rec.approval_date and rec.approved_by):
                raise ValidationError(
                    _('Approval Date and Approved By are required when setting status to Approved.')
                )
