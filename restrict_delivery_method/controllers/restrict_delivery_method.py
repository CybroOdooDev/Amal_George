# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Aysha Shalin (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC
#    LICENSE (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from odoo import _
from odoo.addons.website_sale.controllers.payment import PaymentPortal

from odoo.http import request, route
from odoo.tools import str2bool


class WebsiteSale(PaymentPortal):
    """ This class is the inherited class and uses the function in that class
    and super that function. """
    @route('/shop/checkout', type='http', methods=['GET'], auth='public',
        website=True, sitemap=False)
    def shop_checkout(self, try_skip_step=None, **query_params):
        """ This function is overrode to update the delivery methods with
        removing the restricted ones. """
        try_skip_step = str2bool(try_skip_step or 'false')
        order_sudo = request.website.sale_get_order()
        request.session['sale_last_order_id'] = order_sudo.id

        if redirection := self._check_cart_and_addresses(order_sudo):
            return redirection

        checkout_page_values = self._prepare_checkout_page_values(order_sudo,
                                                                  **query_params)

        can_skip_delivery = True  # Delivery is only needed for deliverable products.
        if order_sudo._has_deliverable_products():
            available_dms = order_sudo._get_delivery_methods()
            checkout_page_values['delivery_methods'] = available_dms
            checkout_page_values.update({'errors': []})
            if delivery_method := order_sudo._get_preferred_delivery_method(available_dms):
                rate = delivery_method.rate_shipment(order_sudo)
                if (
                        not order_sudo.carrier_id
                        or not rate.get('success')
                        or order_sudo.amount_delivery != rate['price']
                ):
                    order_sudo._set_delivery_method(delivery_method, rate=rate)
            delivery_carriers = order_sudo._get_restrict_delivery_method()
            checkout_page_values['delivery_methods'] = delivery_carriers.sudo()

        if try_skip_step and can_skip_delivery:
            return request.redirect('/shop/confirm_order')
        return request.render('website_sale.checkout', checkout_page_values)
