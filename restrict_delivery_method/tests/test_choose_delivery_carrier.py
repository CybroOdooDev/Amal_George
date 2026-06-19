# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestChooseDeliveryCarrier(TransactionCase):
    """Tests for the ChooseDeliveryCarrier wizard extension."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.delivery_product = cls.env['product.product'].create({
            'name': 'Shipping Fee',
            'type': 'service',
        })
        cls.restricted_product_tmpl = cls.env['product.template'].create({
            'name': 'Restricted Sale Product',
            'type': 'consu',
        })
        cls.restricted_product = cls.restricted_product_tmpl.product_variant_ids[0]

        cls.carrier = cls.env['delivery.carrier'].create({
            'name': 'Restricted Carrier',
            'product_id': cls.delivery_product.id,
            'delivery_type': 'fixed',
            'fixed_price': 10.0,
            'restrict_product_ids': [(6, 0, cls.restricted_product_tmpl.ids)],
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Wizard Test Customer'})
        cls.order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'order_line': [(0, 0, {
                'product_id': cls.restricted_product.id,
                'product_uom_qty': 1,
                'price_unit': 50.0,
            })],
        })

    def test_delivery_method_ids_related_field_exists(self):
        """Verify delivery_method_ids related field is present on choose.delivery.carrier."""
        self.assertIn(
            'delivery_method_ids',
            self.env['choose.delivery.carrier']._fields,
        )

    def test_delivery_method_ids_reflects_order(self):
        """The wizard's delivery_method_ids mirrors the sale order's computed value."""
        wizard = self.env['choose.delivery.carrier'].with_context(
            active_id=self.order.id,
            active_model='sale.order',
        ).create({
            'order_id': self.order.id,
            'carrier_id': self.carrier.id,
        })
        self.assertIn(
            self.carrier,
            wizard.delivery_method_ids,
            "Wizard's delivery_method_ids should reflect the sale order's restricted carriers",
        )

    def test_wizard_delivery_method_ids_empty_when_no_restriction(self):
        """The wizard's delivery_method_ids is empty when the order has no restricted product."""
        free_product = self.env['product.product'].create({
            'name': 'Free Product',
            'type': 'consu',
        })
        free_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': free_product.id,
                'product_uom_qty': 1,
                'price_unit': 20.0,
            })],
        })
        wizard = self.env['choose.delivery.carrier'].with_context(
            active_id=free_order.id,
            active_model='sale.order',
        ).create({
            'order_id': free_order.id,
            'carrier_id': self.carrier.id,
        })
        self.assertFalse(
            wizard.delivery_method_ids,
            "Wizard delivery_method_ids should be empty for orders without restricted products",
        )
