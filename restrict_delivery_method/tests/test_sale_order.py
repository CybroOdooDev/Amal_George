# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleOrder(TransactionCase):
    """Tests for the SaleOrder model extensions in restrict_delivery_method."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a delivery product (service type required by delivery.carrier)
        cls.delivery_product = cls.env['product.product'].create({
            'name': 'Shipping Fee',
            'type': 'service',
        })
        # Create a restricted product
        cls.restricted_product_tmpl = cls.env['product.template'].create({
            'name': 'Restricted Sale Product',
            'type': 'consu',
        })
        cls.restricted_product = cls.restricted_product_tmpl.product_variant_ids[0]

        # Create an unrestricted product
        cls.free_product_tmpl = cls.env['product.template'].create({
            'name': 'Free Sale Product',
            'type': 'consu',
        })
        cls.free_product = cls.free_product_tmpl.product_variant_ids[0]

        # Create a carrier that restricts cls.restricted_product_tmpl
        cls.restricted_carrier = cls.env['delivery.carrier'].create({
            'name': 'Restricted Carrier',
            'product_id': cls.delivery_product.id,
            'delivery_type': 'fixed',
            'fixed_price': 10.0,
            'restrict_product_ids': [(6, 0, cls.restricted_product_tmpl.ids)],
        })

        # Customer partner
        cls.partner = cls.env['res.partner'].create({'name': 'Test Customer'})

    def _make_order(self, product):
        """Helper to create a confirmed sale order with a given product."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
                'price_unit': 50.0,
            })],
        })
        return order

    def test_compute_delivery_method_ids_with_restricted_product(self):
        """delivery_method_ids is computed and includes the carrier restricting that product."""
        order = self._make_order(self.restricted_product)
        self.assertIn(
            self.restricted_carrier,
            order.delivery_method_ids,
            "Carrier restricting the order's product should appear in delivery_method_ids",
        )

    def test_compute_delivery_method_ids_without_restricted_product(self):
        """delivery_method_ids is empty when the order has no restricted product."""
        order = self._make_order(self.free_product)
        self.assertFalse(
            order.delivery_method_ids,
            "No carrier should be computed when the product has no restriction",
        )

    def test_delivery_method_ids_field_exists(self):
        """Verify the delivery_method_ids field is present on sale.order."""
        self.assertIn('delivery_method_ids', self.env['sale.order']._fields)

    def test_compute_updates_when_order_line_changes(self):
        """delivery_method_ids recomputes when the order line product changes."""
        order = self._make_order(self.free_product)
        self.assertFalse(order.delivery_method_ids)
        # Add a restricted product line
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.restricted_product.id,
            'product_uom_qty': 1,
            'price_unit': 50.0,
        })
        self.assertIn(self.restricted_carrier, order.delivery_method_ids)
