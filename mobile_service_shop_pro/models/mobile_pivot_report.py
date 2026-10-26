# -- coding: utf-8 --
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Technologies(odoo@cybrosys.com)
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the
#    Software or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NON INFRINGEMENT. IN NO EVENT SHALL
#    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,ARISING
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
###############################################################################

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

    service = fields.Char(
        string='Service Number', readonly=True,
        help="Unique identifier/name of the service request.")
    partner_id = fields.Many2one(
        'res.partner', string="Customer", readonly=True,
        help="Customer associated with the service request.")
    brand_id = fields.Many2one(
        'mobile.brand', string="Mobile Brand", readonly=True,
        help="Brand of the mobile device.")
    imei_no = fields.Char(
        string="IMEI Number", readonly=True,
        help="15-digit IMEI number of the mobile device.")
    model_id = fields.Many2one(
        'brand.model', string="Model", readonly=True,
        help="Model of the mobile brand.")
    date_request = fields.Date(
        string="Requested Date", readonly=True,
        help="Date when the service request was created.")
    return_date = fields.Date(
        string="Return Date", readonly=True,
        help="Expected or actual date the device is returned to the customer.")
    technician_id = fields.Many2one(
        'res.users', string="Technician", readonly=True,
        help="Technician assigned to repair the device.")
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
        help="Current status of the service request.",
    )
    product_tmpl_id = fields.Many2one(
        'product.template', string='Parts Used', readonly=True,
        help="Spare part template used during the repair.")
    complaint_type = fields.Char(
        string='Complaint Types', readonly=True,
        help="Registered customer complaint description.")

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


