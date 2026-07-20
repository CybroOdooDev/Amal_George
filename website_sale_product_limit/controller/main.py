# -*- coding: utf-8 -*-

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request

class website_sale_product_limit(WebsiteSale):
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, tags='', **post):
        website = request.env['website'].get_current_website()
        icp_sudo = self.env['ir.config_parameter'].sudo()
        demo_ppg = icp_sudo.get_param('res.config.settings.product_limit')
        website.shop_ppg = int(demo_ppg)
        return super().shop(page= page, category=category, search=search, min_price=min_price, max_price=max_price, tags=tags, **post)
