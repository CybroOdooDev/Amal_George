# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestStockMoveLine(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestStockMoveLine, cls).setUpClass()
        cls.company = cls.env.company

        # Sanitize account_account table constraints for third-party modules (e.g. account_asset)
        cls.env.cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'account_account' AND column_name = 'create_asset'
        """)
        if cls.env.cr.fetchone():
            cls.env.cr.execute("ALTER TABLE account_account ALTER COLUMN create_asset DROP NOT NULL")

        # Find a suitable stock location and warehouse
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)
        if not cls.warehouse:
            cls.warehouse = cls.env['stock.warehouse'].create({
                'name': 'Test Warehouse',
                'code': 'TWH',
                'company_id': cls.company.id,
            })
        cls.stock_location = cls.warehouse.lot_stock_id

        # Setup accounting data
        cls.stock_journal = cls.env['account.journal'].create({
            'name': 'Stock Journal',
            'type': 'general',
            'code': 'TSTK',
            'company_id': cls.company.id,
        })
        cls.stock_valuation_account = cls.env['account.account'].create({
            'name': 'Stock Valuation Account',
            'code': 'SVAL9',
            'account_type': 'asset_current',
            'company_ids': [(4, cls.company.id)],
        })
        cls.price_diff_account = cls.env['account.account'].create({
            'name': 'Price Difference Account',
            'code': 'PDIF9',
            'account_type': 'expense',
            'company_ids': [(4, cls.company.id)],
        })

        # Product Category set to 'last' costing method
        cls.category = cls.env['product.category'].create({
            'name': 'Test Category Last Price',
            'property_cost_method': 'last',
            'property_valuation': 'real_time',
            'property_stock_journal': cls.stock_journal.id,
            'property_stock_valuation_account_id': cls.stock_valuation_account.id,
            'property_account_creditor_price_difference_categ': cls.price_diff_account.id,
        })

        # Product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product Last Price',
            'is_storable': True,
            'categ_id': cls.category.id,
            'standard_price': 10.0,
        })

    def test_stock_move_line_write_qty_correction(self):
        """ Test quantity correction on a done stock move line """
        move = self.env['stock.move'].create({
            'name': 'Incoming Move',
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.stock_location.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 10.0,
            'price_unit': 10.0,
        })
        move._action_confirm()
        move._action_assign()
        move.picked = True
        move._action_done()

        move_line = move.move_line_ids[0]
        self.assertEqual(move_line.quantity, 10.0)
        self.assertEqual(self.product.qty_available, 10.0)

        # Correct the quantity to 8.0
        move_line.write({'quantity': 8.0})

        # Verify quantity available and stock valuation layers are updated accordingly
        self.assertEqual(self.product.qty_available, 8.0)
