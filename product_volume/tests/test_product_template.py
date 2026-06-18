# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestProductTemplateVolume(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestProductTemplateVolume, cls).setUpClass()
        cls.product_template_model = cls.env['product.template']

    def test_product_measures_meters(self):
        """ Test volume calculation with length UoM set to meters """
        product = self.product_template_model.create({
            'name': 'Test Product Meters',
            'length': '2.0',
            'breadth': '3.0',
            'height': '4.0',
            'length_uom': 'meters',
            'volume_uom': 'cubic_meters',
        })
        product._onchange_product_measures()
        self.assertAlmostEqual(product.volume, 24.0, places=2)

    def test_product_measures_centimeters(self):
        """ Test volume calculation with length UoM set to centimeters """
        product = self.product_template_model.create({
            'name': 'Test Product Centimeters',
            'length': '100.0',
            'breadth': '200.0',
            'height': '300.0',
            'length_uom': 'centimeters',
            'volume_uom': 'cubic_meters',
        })
        product._onchange_product_measures()
        self.assertAlmostEqual(product.volume, 6.0, places=2)

    def test_product_measures_inches(self):
        """ Test volume calculation with length UoM set to inches """
        product = self.product_template_model.create({
            'name': 'Test Product Inches',
            'length': '10.0',
            'breadth': '20.0',
            'height': '30.0',
            'length_uom': 'inches',
            'volume_uom': 'cubic_meters',
        })
        product._onchange_product_measures()
        expected_volume = (10.0 * 20.0 * 30.0) / 61023.7
        self.assertAlmostEqual(product.volume, expected_volume, places=2)

    def test_product_measures_feet(self):
        """ Test volume calculation with length UoM set to feet """
        product = self.product_template_model.create({
            'name': 'Test Product Feet',
            'length': '10.0',
            'breadth': '10.0',
            'height': '10.0',
            'length_uom': 'feet',
            'volume_uom': 'cubic_meters',
        })
        product._onchange_product_measures()
        expected_volume = (10.0 * 10.0 * 10.0) / 35.3147
        self.assertAlmostEqual(product.volume, expected_volume, places=2)

    def test_product_measures_yards(self):
        """ Test volume calculation with length UoM set to yards """
        product = self.product_template_model.create({
            'name': 'Test Product Yards',
            'length': '10.0',
            'breadth': '10.0',
            'height': '10.0',
            'length_uom': 'yards',
            'volume_uom': 'cubic_meters',
        })
        product._onchange_product_measures()
        expected_volume = (10.0 * 10.0 * 10.0) / 1.308
        self.assertAlmostEqual(product.volume, expected_volume, places=2)

    def test_product_measures_volume_uoms(self):
        """ Test target volume fields conversion to different volume UoMs """
        # Test cubic_inches
        product_inches = self.product_template_model.create({
            'name': 'Test Volume Cubic Inches',
            'length': '2.0',
            'breadth': '3.0',
            'height': '4.0',
            'length_uom': 'meters',
            'volume_uom': 'cubic_inches',
        })
        product_inches._onchange_product_measures()
        self.assertAlmostEqual(product_inches.volume, 24.0 * 61023.7, places=2)

        # Test cubic_feet
        product_feet = self.product_template_model.create({
            'name': 'Test Volume Cubic Feet',
            'length': '2.0',
            'breadth': '3.0',
            'height': '4.0',
            'length_uom': 'meters',
            'volume_uom': 'cubic_feet',
        })
        product_feet._onchange_product_measures()
        self.assertAlmostEqual(product_feet.volume, 24.0 * 35.3147, places=2)

        # Test cubic_yards
        product_yards = self.product_template_model.create({
            'name': 'Test Volume Cubic Yards',
            'length': '2.0',
            'breadth': '3.0',
            'height': '4.0',
            'length_uom': 'meters',
            'volume_uom': 'cubic_yards',
        })
        product_yards._onchange_product_measures()
        self.assertAlmostEqual(product_yards.volume, 24.0 * 1.308, places=2)

    def test_product_measures_empty_and_zero(self):
        """ Test that empty, zero or None fields don't cause crashes and result in 0 volume """
        product_empty = self.product_template_model.create({
            'name': 'Test Product Empty Measures',
            'length': False,
            'breadth': False,
            'height': False,
            'length_uom': 'meters',
            'volume_uom': 'cubic_meters',
        })
        product_empty._onchange_product_measures()
        self.assertEqual(product_empty.volume, 0.0)

        product_empty_str = self.product_template_model.create({
            'name': 'Test Product Empty String Measures',
            'length': '',
            'breadth': '',
            'height': '',
            'length_uom': 'meters',
            'volume_uom': 'cubic_meters',
        })
        product_empty_str._onchange_product_measures()
        self.assertEqual(product_empty_str.volume, 0.0)
