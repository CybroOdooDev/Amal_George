# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <https://www.gnu.org/licenses/>.
#
#############################################################################

from odoo import models


class StockLocation(models.Model):
    """Routes material to the sub-area providing the storage class it requires."""
    _inherit = 'stock.location'

    def _get_putaway_strategy(self, product, *args, **kwargs):
        """Resolve the product's storage class into a physical sub-area.

        Inserts a single step ahead of native putaway: when the product declares
        a storage class that this location does not itself provide, the search is
        narrowed to the descendant tagged with that class, and native putaway
        then runs *inside* it so any bin-level rules configured there still
        apply. Resolution order:

        1. No storage class on the product -> native behaviour, untouched.
        2. This location already provides the class -> native behaviour.
        3. A matching descendant exists -> native putaway within that sub-area.
        4. Class set but no matching descendant -> native behaviour, which lands
           the material on the area root. Wrong bin, but visibly wrong rather
           than silently misrouted.

        The signature deliberately forwards ``*args, **kwargs`` because native
        putaway gained keyword arguments across Odoo versions; enumerating them
        here would break on the next change.

        :param product: product.product being put away.
        :return: stock.location the material has to be put in.
        """
        required = product.storage_category_id
        if required and self.storage_category_id != required:
            area = self.search([
                ('id', 'child_of', self.id),
                ('usage', '=', 'internal'),
                ('storage_category_id', '=', required.id),
            ], limit=1, order='complete_name')
            if area:
                return super(StockLocation, area)._get_putaway_strategy(
                    product, *args, **kwargs) or area
        return super()._get_putaway_strategy(product, *args, **kwargs)

    def _pharma_storage_categories(self):
        """Walk up location_id accumulating storage_category_id.

        A rack inside a tagged area inherits that area's storage class, so the
        enforcement guard has to consider the whole ancestor chain rather than
        the destination's own category alone.

        :return: stock.storage.category recordset provided by this location or
                 any of its ancestors.
        """
        self.ensure_one()
        categories = self.env['stock.storage.category']
        location = self
        while location:
            categories |= location.storage_category_id
            location = location.location_id
        return categories
