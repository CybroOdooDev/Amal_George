# -*- coding: utf-8 -*-
################################################################################
#
#    Mobile Service Management Pro — Odoo 19
#    Pivot/Graph analytics model (PostgreSQL view)
#
################################################################################
from odoo import fields, models, tools


class MobilePivotReport(models.Model):
    """Read-only analytics model backed by a PostgreSQL view.
    Aggregates service jobs, parts, technicians and complaint types
    for pivot table and graph analysis.
    """
    _name = "mobile.pivot.report"
    _description = "Mobile Service Statistics"
    _auto = False
    _rec_name = 'service'

    service = fields.Char(string='Service Number', readonly=True)
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True)
    brand_id = fields.Many2one('mobile.brand', string="Mobile Brand", readonly=True)
    imei_no = fields.Char(string="IMEI Number", readonly=True)
    model_id = fields.Many2one('brand.model', string="Model", readonly=True)
    date_request = fields.Date(string="Requested Date", readonly=True)
    return_date = fields.Date(string="Return Date", readonly=True)
    technician_id = fields.Many2one('res.users', string="Technician", readonly=True)
    service_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('assigned', 'Assigned'),
            ('completed', 'Completed'),
            ('returned', 'Returned'),
            ('not_solved', 'Not Solved'),
        ],
        string='Service Status',
        readonly=True,
    )
    product_tmpl_id = fields.Many2one(
        'product.template', string='Parts Used', readonly=True)
    complaint_type = fields.Char(string='Complaint Types', readonly=True)

    def init(self):
        """Create or replace the PostgreSQL view backing this model."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    ROW_NUMBER() OVER ()               AS id,
                    m.name                             AS service,
                    m.person_name                      AS partner_id,
                    m.brand_name                       AS brand_id,
                    m.imei_no                          AS imei_no,
                    m.model_name                       AS model_id,
                    m.date_request                     AS date_request,
                    m.return_date                      AS return_date,
                    m.technician_name                  AS technician_id,
                    m.service_state                    AS service_state,
                    pt.id                              AS product_tmpl_id,
                    STRING_AGG(
                        COALESCE(mc.complaint_type, ''), ','
                    )                                  AS complaint_type
                FROM mobile_service m
                LEFT JOIN product_order_line po
                    ON m.id = po.product_order_id
                LEFT JOIN product_product pp
                    ON pp.id = po.product_id
                LEFT JOIN product_template pt
                    ON pp.product_tmpl_id = pt.id
                LEFT JOIN mobile_complaint_tree mct
                    ON m.id = mct.complaint_id
                LEFT JOIN mobile_complaint mc
                    ON mc.id = mct.complaint_type_tree
                GROUP BY
                    pt.id, po.id, m.id,
                    m.person_name, m.imei_no, m.model_name,
                    m.date_request, m.technician_name, m.service_state
            )
        """
        self.env.cr.execute(query)
