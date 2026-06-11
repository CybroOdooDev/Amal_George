# -*- coding: utf-8 -*-
from odoo import api, fields, models

class StockLot(models.Model):
    """
    Extends stock.lot with pharma lot status, expiry, and QA traceability.
    Lots with status Quarantine, Rejected, On Hold, or Recalled are blocked
    from being issued to production or dispatched to customers.
    """
    _inherit = 'stock.lot'

    # ── Lot Status ────────────────────────────────────────────────────────────
    lot_status = fields.Selection(
        selection=[
            ('quarantine', 'Quarantine'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('on_hold', 'On Hold'),
            ('released', 'Released (FG)'),
            ('recalled', 'Recalled'),
        ],
        string='Lot Status',
        default='quarantine',
        required=True,
        tracking=True,
        index=True,
        help='Controls which operations are permitted for this lot. '
             'Quarantine/Rejected/On Hold/Recalled lots are blocked from '
             'production and dispatch.',
    )

    # ── Status Change Audit ───────────────────────────────────────────────────
    status_changed_by = fields.Many2one(
        comodel_name='res.users',
        string='Status Changed By',
        copy=False,
        tracking=True,
    )

    status_changed_on = fields.Datetime(
        string='Status Changed On',
        copy=False,
        tracking=True,
    )

    # ── QC / Expiry ────────────────────────────────────────────────────────────
    expiry_date = fields.Date(
        string='Expiry Date',
        tracking=True,
        help='Expiry date of this lot, calculated from manufacture date and shelf life.',
    )

    manufacture_date = fields.Date(
        string='Manufacture Date',
        tracking=True,
    )

    retest_date = fields.Date(
        string='Re-test Date',
        tracking=True,
        help='Date by which this lot must be re-tested for continued use.',
    )

    # ── Smart Button for QC Tests ──────────────────────────────────────────────
    qc_test_count = fields.Integer(
        string='QC Tests',
        compute='_compute_qc_test_count'
    )

    def _compute_qc_test_count(self):
        for lot in self:
            lot.qc_test_count = self.env['pharma.qc.test.order'].search_count([('lot_id', '=', lot.id)])

    def action_view_qc_tests(self):
        self.ensure_one()
        return {
            'name': 'QC Test Orders',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'pharma.qc.test.order',
            'domain': [('lot_id', '=', self.id)],
            'context': {'default_lot_id': self.id},
        }

    # ── Vendor CoA ─────────────────────────────────────────────────────────────
    vendor_coa = fields.Binary(
        string="Vendor CoA",
        attachment=True,
        help="Vendor's Certificate of Analysis attached at goods receipt.",
    )

    vendor_coa_filename = fields.Char(string='CoA Filename')

    vendor_lot_number = fields.Char(
        string="Vendor's Lot Number",
        help="The lot/batch number as printed on the vendor's label or CoA.",
        tracking=True,
    )

    # ── Disposition ────────────────────────────────────────────────────────────
    disposition_remarks = fields.Text(
        string='Disposition Remarks',
        tracking=True,
        help='QA justification for releasing, rejecting, or holding this lot.',
    )

    # ── Override write to stamp status change audit ──────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('lot_status'):
                vals['status_changed_by'] = self.env.user.id
                vals['status_changed_on'] = fields.Datetime.now()
        return super().create(vals_list)

    def write(self, vals):
        lots_to_trigger = self.env['stock.lot']
        if 'lot_status' in vals and vals['lot_status'] == 'approved':
            lots_to_trigger = self.filtered(lambda l: l.lot_status == 'quarantine')

        if 'lot_status' in vals:
            vals['status_changed_by'] = self.env.user.id
            vals['status_changed_on'] = fields.Datetime.now()

        res = super().write(vals)

        for lot in lots_to_trigger:
            lot._create_qc_test_order()

        return res

    def _create_qc_test_order(self):
        self.ensure_one()
        product_tmpl = self.product_id.product_tmpl_id
        if not product_tmpl:
            return

        spec = self.env['pharma.qc.spec'].search([
            ('product_id', '=', product_tmpl.id),
            ('stage', '=', 'incoming'),
            ('state', '=', 'approved')
        ], order='version desc', limit=1)

        vals = {
            'lot_id': self.id,
            'product_id': product_tmpl.id,
            'stage': 'incoming',
            'status': 'draft',
        }
        if spec:
            vals['spec_id'] = spec.id

        self.env['pharma.qc.test.order'].create(vals)

    # ── Convenience actions ────────────────────────────────────────────────────
    def action_approve_lot(self):
        self.write({'lot_status': 'approved'})

    def action_reject_lot(self):
        self.write({'lot_status': 'rejected'})

    def action_hold_lot(self):
        self.write({'lot_status': 'on_hold'})
