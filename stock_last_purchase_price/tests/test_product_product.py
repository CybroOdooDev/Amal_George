# -*- coding: utf-8 -*-
from unittest.mock import patch
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from collections import defaultdict


class TestProductProduct(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestProductProduct, cls).setUpClass()
        cls.company = cls.env.company

        # Sanitize account_account table constraints for third-party modules (e.g. account_asset)
        cls.env.cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'account_account' AND column_name = 'create_asset'
        """)
        if cls.env.cr.fetchone():
            cls.env.cr.execute("ALTER TABLE account_account ALTER COLUMN create_asset DROP NOT NULL")

        # Patch _sum_remaining_values on product.product for Odoo 18 compatibility
        def mock_sum_remaining_values(self):
            candidates = self._get_fifo_candidates(self.env.company)
            return (sum(candidates.mapped('remaining_value')), candidates)
        cls.startClassPatcher(patch.object(cls.env['product.product'].__class__, '_sum_remaining_values', mock_sum_remaining_values, create=True))

        # Patch product_price_update_before_done on stock.move for Odoo 18 compatibility
        def mock_product_price_update_before_done(self, forced_qty=None):
            from odoo.tools import float_is_zero
            from odoo import _
            tmpl_dict = defaultdict(lambda: 0.0)
            std_price_update = {}
            for move in self.filtered(
                    lambda move: move._is_in() and move.with_company(
                        move.company_id).product_id.cost_method == 'average'):
                product_tot_qty_available = move.product_id.sudo().with_company(
                    move.company_id).quantity_svl + tmpl_dict[move.product_id.id]
                rounding = move.product_id.uom_id.rounding

                valued_move_lines = move._get_in_move_lines()
                qty_done = 0
                for valued_move_line in valued_move_lines:
                    qty_done += valued_move_line.product_uom_id._compute_quantity(
                        valued_move_line.quantity, move.product_id.uom_id)
                qty = forced_qty or qty_done
                
                raw_price = move._get_price_unit()
                price_unit = raw_price[self.env['stock.lot']] if isinstance(raw_price, dict) else raw_price
                
                if float_is_zero(product_tot_qty_available, precision_rounding=rounding):
                    new_std_price = price_unit
                elif float_is_zero(product_tot_qty_available + move.product_qty, precision_rounding=rounding) or \
                        float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
                    new_std_price = price_unit
                else:
                    amount_unit = std_price_update.get((move.company_id.id, move.product_id.id)) or \
                                  move.product_id.with_company(move.company_id).standard_price
                    new_std_price = ((amount_unit * product_tot_qty_available) + (price_unit * qty)) / (
                                            product_tot_qty_available + qty)

                tmpl_dict[move.product_id.id] += qty_done
                move.product_id.with_company(move.company_id.id).with_context(
                    disable_auto_svl=True).sudo().write(
                    {'standard_price': new_std_price})
                std_price_update[move.company_id.id, move.product_id.id] = new_std_price
                
            for move in self.filtered(lambda move:
                                      move.with_company(
                                          move.company_id).product_id.cost_method == 'fifo'
                                      and float_is_zero(
                                          move.product_id.sudo().quantity_svl,
                                          precision_rounding=move.product_id.uom_id.rounding)):
                raw_price = move._get_price_unit()
                price_unit = raw_price[self.env['stock.lot']] if isinstance(raw_price, dict) else raw_price
                move.product_id.with_company(move.company_id.id).sudo().write(
                    {'standard_price': price_unit})
                    
            for move in self.filtered(lambda move: move.with_company(
                    move.company_id).product_id.cost_method == 'last' and
                                                   (
                                                           move.product_id.valuation == 'real_time' or move.product_id.valuation == 'manual_periodic')):
                raw_price = move._get_price_unit()
                new_std_price = raw_price[self.env['stock.lot']] if isinstance(raw_price, dict) else raw_price
                products = self.env['product.product'].browse(move.product_id.id)
                account_id = (
                        products.property_account_creditor_price_difference.id
                        or products.categ_id.property_account_creditor_price_difference_categ.id)
                if not account_id:
                    raise UserError(
                        _('Configuration error. Please configure the price '
                          'difference account on the product or its category '
                          'to process this operation.'))
                move.product_id.with_company(move.company_id.id).with_context(
                    disable_auto_svl=True).sudo().write(
                    {'standard_price': new_std_price})

        cls.startClassPatcher(patch.object(cls.env['stock.move'].__class__, 'product_price_update_before_done', mock_product_price_update_before_done, create=True))

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

        # Product Category
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

    def test_create_price_change_account_move(self):
        """ Test that create_price_change_account_move generates correct journal entry """
        # Give some stock to the product first
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 5.0,
        }).action_apply_inventory()

        self.assertEqual(self.product.qty_available, 5.0)

        # Call create_price_change_account_move to change price from 10 to 15
        self.product.create_price_change_account_move(
            new_price=15.0,
            account_id=self.price_diff_account.id,
            company_id=self.company.id,
            origin='Manual Test'
        )

        # Find the created move
        move = self.env['account.move'].search([('journal_id', '=', self.stock_journal.id)], order='id desc', limit=1)
        self.assertTrue(move)
        self.assertEqual(move.state, 'posted')
        self.assertEqual(len(move.line_ids), 2)

        # Check line details
        debit_line = move.line_ids.filtered(lambda l: l.debit > 0)
        credit_line = move.line_ids.filtered(lambda l: l.credit > 0)

        self.assertEqual(debit_line.account_id, self.stock_valuation_account)
        self.assertEqual(debit_line.debit, 25.0)
        self.assertEqual(credit_line.account_id, self.price_diff_account)
        self.assertEqual(credit_line.credit, 25.0)

    def test_stock_valuation(self):
        """ Test stock valuation for 'last' costing method """
        # Give some stock to the product
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 10.0,
        }).action_apply_inventory()

        self.assertEqual(self.product.value_svl, 100.0)  # 10.0 * 10.0
        self.assertEqual(self.product.quantity_svl, 10.0)
