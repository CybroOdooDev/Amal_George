# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.exceptions import ValidationError
from psycopg2 import IntegrityError
from odoo.tools import mute_logger

@tagged('post_install', '-at_install')
class TestProductSupplierinfo(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Supplier Vendor',
            'default_discount': 15.0,
        })
        cls.product = cls.env['product.template'].create({
            'name': 'Supplier Product',
            'type': 'consu',
        })

    def test_supplierinfo_discount_onchange(self):
        """Test that default_discount is assigned to supplierinfo discount on onchange."""
        supplier_info = self.env['product.supplierinfo'].new({
            'partner_id': self.partner.id,
            'product_tmpl_id': self.product.id,
        })
        supplier_info._onchange_discount()
        self.assertEqual(supplier_info.discount, 15.0)

    def test_supplierinfo_discount_sql_constraint(self):
        """Test maximum discount check constraint (<= 100.0)."""
        si = self.env['product.supplierinfo'].create({
            'partner_id': self.partner.id,
            'product_tmpl_id': self.product.id,
            'discount': 50.0,
            'price': 100.0,
        })
        self.assertEqual(si.discount, 50.0)
        
        with mute_logger('odoo.sql_db'):
            try:
                with self.env.cr.savepoint():
                    self.env['product.supplierinfo'].create({
                        'partner_id': self.partner.id,
                        'product_tmpl_id': self.product.id,
                        'discount': 120.0,
                        'price': 100.0,
                    })
            except (ValidationError, IntegrityError):
                pass
            else:
                self.fail("ValidationError or IntegrityError not raised for discount > 100")
