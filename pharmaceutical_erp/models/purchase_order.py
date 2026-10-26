# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools.translate import _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    """
    Extends purchase.order with pharma approval state and AVL enforcement.
    On confirmation the system checks that every product-vendor pair exists
    in pharma.avl with status 'approved'.
    """
    _inherit = 'purchase.order'

    # ── Pharma Approval State ─────────────────────────────────────────────────
    pharma_approval_state = fields.Selection(
        selection=[
            ('pending', 'Pending QA Review'),
            ('approved', 'QA Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Pharma Approval',
        default='pending',
        copy=False,
        tracking=True,
        help='QA review status for this purchase order.',
    )

    pharma_approved_by = fields.Many2one(
        comodel_name='res.users',
        string='Pharma Approved By',
        copy=False,
        tracking=True,
    )

    pharma_approval_date = fields.Date(
        string='Pharma Approval Date',
        copy=False,
        tracking=True,
    )

    pharma_notes = fields.Text(
        string='Pharma Notes',
        help='QA remarks or conditions attached to this PO.',
    )

    # ── AVL Check on Confirm ──────────────────────────────────────────────────
    def button_confirm(self):
        """Block PO confirmation if any product-vendor pair is not on the AVL."""
        for order in self:
            order._check_avl()
        return super().button_confirm()

    def _check_avl(self):
        """
        For every line that carries a pharma product, verify the vendor is
        on the Approved Vendor List with status 'approved'.
        Lines without a product_type_pharma are skipped (non-GMP items).
        """
        partner = self.partner_id
        for line in self.order_line:
            product_tmpl = line.product_id.product_tmpl_id
            # Only enforce AVL for products explicitly classified as pharma materials
            if not product_tmpl.product_type_pharma:
                continue
            avl = self.env['pharma.avl'].search([
                ('product_id', '=', product_tmpl.id),
                ('vendor_id', '=', partner.id),
                ('status', '=', 'approved'),
            ], limit=1)
            if not avl:
                raise UserError(
                    _(
                        'AVL Check Failed: Vendor "%(vendor)s" is not on the '
                        'Approved Vendor List for product "%(product)s".\n\n'
                        'Please add the vendor to the AVL with Approved status '
                        'before confirming this purchase order.',
                        vendor=partner.name,
                        product=product_tmpl.name,
                    )
                )

    # ── QA Approve / Reject Actions ────────────────────────────────────────────
    def action_pharma_approve(self):
        self.write({
            'pharma_approval_state': 'approved',
            'pharma_approved_by': self.env.user.id,
            'pharma_approval_date': fields.Date.today(),
        })

    def action_pharma_reject(self):
        self.write({'pharma_approval_state': 'rejected'})
