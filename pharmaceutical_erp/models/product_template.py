# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ── Pharma Classification ───────────────────────────────────────────────
    product_type_pharma = fields.Selection(
        selection=[
            ('api', 'API (Active Pharmaceutical Ingredient)'),
            ('excipient', 'Excipient'),
            ('finished_goods', 'Finished Goods'),
            ('packaging', 'Packaging Material'),
            ('intermediate', 'Intermediate / Bulk'),
        ],
        string='Pharma Material Type',
        help='Classifies this product within the pharmaceutical manufacturing context.',
        tracking=True,
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
        help='International standard this product is tested against.',
        tracking=True,
    )

    shelf_life_months = fields.Integer(
        string='Shelf Life (Months)',
        help='Number of months this product remains valid after manufacture.',
        tracking=True,
    )

    storage_conditions = fields.Char(
        string='Storage Conditions',
        help='Temperature, light, and humidity conditions (e.g. "Store below 25°C, protect from light").',
        tracking=True,
    )

    # ── Regulatory / Licensing ──────────────────────────────────────────────
    drug_license_no = fields.Char(
        string='Drug License No.',
        help='Regulatory license number for this product.',
        tracking=True,
    )

    hsn_code = fields.Char(
        string='HSN Code',
        help='Harmonised System Nomenclature code for customs and GST.',
    )

    # ── Approved Vendor List (AVL) ──────────────────────────────────────────
    avl_ids = fields.One2many(
        comodel_name='pharma.avl',
        inverse_name='product_id',
        string='Approved Vendor List',
        help='Vendors approved by QA to supply this material.',
    )

    avl_count = fields.Integer(
        string='AVL Count',
        compute='_compute_avl_count',
    )

    # ── QC Specifications ───────────────────────────────────────────────────
    qc_spec_ids = fields.One2many(
        comodel_name='pharma.qc.spec',
        inverse_name='product_id',
        string='QC Specifications',
        help='All quality control specifications linked to this product.',
    )

    qc_spec_count = fields.Integer(
        string='QC Spec Count',
        compute='_compute_qc_spec_count',
    )

    # ── Computes ────────────────────────────────────────────────────────────
    @api.depends('avl_ids')
    def _compute_avl_count(self):
        for rec in self:
            rec.avl_count = len(rec.avl_ids)

    @api.depends('qc_spec_ids')
    def _compute_qc_spec_count(self):
        for rec in self:
            rec.qc_spec_count = len(rec.qc_spec_ids)

    # ── Constraints ─────────────────────────────────────────────────────────
    @api.constrains('shelf_life_months')
    def _check_shelf_life(self):
        for rec in self:
            if rec.shelf_life_months and rec.shelf_life_months < 0:
                raise ValidationError(_('Shelf life cannot be negative.'))
