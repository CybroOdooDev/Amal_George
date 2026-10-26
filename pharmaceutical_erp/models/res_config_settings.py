# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vendor_qualification = fields.Boolean(
        string="Vendor Qualification",
        config_parameter='pharmaceutical_erp.vendor_qualification',
        help="Enable vendor qualification checks.",
        default="False",
    )

    audit_trail = fields.Boolean(
        string="Audit Trail",
        config_parameter='pharmaceutical_erp.audit_trail',
        help="Enable audit trail to track changes in critical records.",
        default=False,
    )

    def set_values(self):
        super().set_values()
        group_user = self.env.ref('base.group_user')
        group_vq = self.env.ref('pharmaceutical_erp.group_vendor_qualification', raise_if_not_found=False)
        if group_vq:
            if self.vendor_qualification:
                group_user.write({'implied_ids': [(4, group_vq.id)]})
            else:
                group_user.write({'implied_ids': [(3, group_vq.id)]})
