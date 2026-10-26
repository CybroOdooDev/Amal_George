from ast import literal_eval
from odoo import api, fields, models
class ResConfigSettings(models.TransientModel):
    """Extension of 'res.config.settings' for configuring delivery settings."""
    _inherit = 'res.config.settings'
    product_limit = fields.Integer(string=' Set Product Limit')

    @api.model
    def get_values(self):
        """Get the values from settings."""
        res = super(ResConfigSettings, self).get_values()
        icp_sudo = self.env['ir.config_parameter'].sudo()
        product_limit = icp_sudo.get_param('res.config.settings.product_limit')
        res.update(
            product_limit=product_limit,
        )
        return res
    def set_values(self):
        """Set the values. The new values are stored in the configuration parameters."""
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'res.config.settings.product_limit', self.product_limit)
        # self.env['website'].shop_ppg= self.product_limit
        return res
