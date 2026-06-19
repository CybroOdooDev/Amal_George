# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestRestrictDeliveryMethod(TransactionCase):
    """Integration tests for the restrict_delivery_method module."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.delivery_product = cls.env['product.product'].create({
            'name': 'Shipping Fee Integration',
            'type': 'service',
        })
        cls.product_tmpl = cls.env['product.template'].create({
            'name': 'Integration Test Product',
            'type': 'consu',
        })
        cls.product = cls.product_tmpl.product_variant_ids[0]
        cls.partner = cls.env['res.partner'].create({'name': 'Integration Customer'})

    def test_module_fields_exist_on_delivery_carrier(self):
        """Verify that restrict_product_ids and partner_warning fields exist on delivery.carrier."""
        carrier_fields = self.env['delivery.carrier']._fields
        self.assertIn('restrict_product_ids', carrier_fields)
        self.assertIn('partner_warning', carrier_fields)

    def test_module_field_exists_on_sale_order(self):
        """Verify that delivery_method_ids field exists on sale.order."""
        self.assertIn('delivery_method_ids', self.env['sale.order']._fields)

    def test_module_field_exists_on_choose_delivery_carrier(self):
        """Verify that delivery_method_ids field exists on choose.delivery.carrier."""
        self.assertIn(
            'delivery_method_ids',
            self.env['choose.delivery.carrier']._fields,
        )

    def test_carrier_restriction_linked_to_product_end_to_end(self):
        """End-to-end: product restricted on carrier → sale order picks up the restriction."""
        carrier = self.env['delivery.carrier'].create({
            'name': 'E2E Carrier',
            'product_id': self.delivery_product.id,
            'delivery_type': 'fixed',
            'fixed_price': 15.0,
            'restrict_product_ids': [(6, 0, self.product_tmpl.ids)],
        })
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'price_unit': 100.0,
            })],
        })
        self.assertIn(
            carrier,
            order.delivery_method_ids,
            "E2E: restricted carrier must appear in sale order's delivery_method_ids",
        )
        # Verify partner_warning was set via onchange logic
        carrier._onchange_restrict_product_ids()
        self.assertTrue(carrier.partner_warning)

    def test_carrier_restriction_cleared(self):
        """Removing restriction clears delivery_method_ids on a new sale order."""
        carrier = self.env['delivery.carrier'].create({
            'name': 'Clearable Carrier',
            'product_id': self.delivery_product.id,
            'delivery_type': 'fixed',
            'fixed_price': 5.0,
            'restrict_product_ids': [(6, 0, self.product_tmpl.ids)],
        })
        # Order with restriction → carrier appears
        order_with = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 50.0,
            })],
        })
        self.assertIn(carrier, order_with.delivery_method_ids)

        # Now remove the restriction
        carrier.restrict_product_ids = [(5, 0, 0)]

        # A fresh order should no longer have this carrier in delivery_method_ids
        order_without = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 50.0,
            })],
        })
        self.assertNotIn(carrier, order_without.delivery_method_ids)

    def test_notification_action_structure(self):
        """Verify action_notification returns a valid client action."""
        carrier = self.env['delivery.carrier'].create({
            'name': 'Notification Carrier',
            'product_id': self.delivery_product.id,
            'delivery_type': 'fixed',
            'fixed_price': 0.0,
        })
        action = carrier.action_notification()
        self.assertEqual(action['type'], 'ir.actions.client')
        self.assertEqual(action['tag'], 'display_notification')
        self.assertIn('params', action)
        self.assertEqual(action['params']['type'], 'warning')
