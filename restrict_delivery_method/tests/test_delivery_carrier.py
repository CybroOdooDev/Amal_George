# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestDeliveryCarrier(TransactionCase):
    """Tests for the DeliveryCarrier model extensions in restrict_delivery_method."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_tmpl = cls.env['product.template'].create({
            'name': 'Restricted Product',
            'type': 'consu',
        })
        cls.carrier = cls.env['delivery.carrier'].create({
            'name': 'Test Carrier',
            'product_id': cls.env['product.product'].search([
                ('type', '=', 'service')
            ], limit=1).id or cls.env['product.product'].create({
                'name': 'Delivery Product',
                'type': 'service',
            }).id,
            'delivery_type': 'fixed',
            'fixed_price': 5.0,
        })

    def test_restrict_product_ids_field(self):
        """Test that restrict_product_ids field stores products correctly."""
        self.carrier.restrict_product_ids = [(6, 0, self.product_tmpl.ids)]
        self.assertIn(self.product_tmpl, self.carrier.restrict_product_ids)

    def test_partner_warning_field_default(self):
        """Test that partner_warning defaults to False on a new carrier."""
        new_carrier = self.env['delivery.carrier'].create({
            'name': 'Another Carrier',
            'product_id': self.carrier.product_id.id,
            'delivery_type': 'fixed',
            'fixed_price': 0.0,
        })
        self.assertFalse(new_carrier.partner_warning)

    def test_action_notification(self):
        """Test action_notification returns the correct client action dict."""
        result = self.carrier.action_notification()
        self.assertEqual(result.get('type'), 'ir.actions.client')
        self.assertEqual(result.get('tag'), 'display_notification')
        params = result.get('params', {})
        self.assertEqual(params.get('title'), 'Warning')
        self.assertEqual(params.get('type'), 'warning')
        self.assertFalse(params.get('sticky'))
        self.assertIn('cannot be restricted', params.get('message', ''))

    def test_onchange_restrict_product_ids_set(self):
        """Test partner_warning becomes True when restrict_product_ids is set."""
        self.carrier.restrict_product_ids = [(6, 0, self.product_tmpl.ids)]
        self.carrier._onchange_restrict_product_ids()
        self.assertTrue(self.carrier.partner_warning)

    def test_onchange_restrict_product_ids_cleared(self):
        """Test partner_warning becomes False when restrict_product_ids is cleared."""
        self.carrier.restrict_product_ids = [(6, 0, self.product_tmpl.ids)]
        self.carrier._onchange_restrict_product_ids()
        self.assertTrue(self.carrier.partner_warning)
        # Now clear the restriction
        self.carrier.restrict_product_ids = [(5, 0, 0)]
        self.carrier._onchange_restrict_product_ids()
        self.assertFalse(self.carrier.partner_warning)

    def test_restrict_product_ids_multiple_products(self):
        """Test that multiple products can be added to restrict_product_ids."""
        product2 = self.env['product.template'].create({
            'name': 'Restricted Product 2',
            'type': 'consu',
        })
        self.carrier.restrict_product_ids = [
            (6, 0, [self.product_tmpl.id, product2.id])
        ]
        self.assertEqual(len(self.carrier.restrict_product_ids), 2)
        self.assertIn(self.product_tmpl, self.carrier.restrict_product_ids)
        self.assertIn(product2, self.carrier.restrict_product_ids)
