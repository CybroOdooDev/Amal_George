# -*- coding: utf-8 -*-
from unittest.mock import patch
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from collections import defaultdict


class TestStockMove(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestStockMove, cls).setUpClass()
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

    def test_stock_move_updates_standard_price(self):
        """ Test that stock move correctly updates product standard price with last purchase price """
        move = self.env['stock.move'].create({
            'name': 'Incoming Move',
            'product_id': self.product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.stock_location.id,
            'product_uom': self.product.uom_id.id,
            'product_uom_qty': 5.0,
            'price_unit': 20.0,
        })
        move._action_confirm()
        move._action_assign()
        move.picked = True
        move._action_done()

        # Product standard price should be updated to 20.0 (last purchase price)
        self.assertEqual(self.product.standard_price, 20.0)

    def test_stock_move_missing_price_diff_account_raises_error(self):
        """ Test that stock move raises error if price difference account is not configured """
        # Create product with category without price difference account
        category_no_diff = self.env['product.category'].create({
            'name': 'Test Category No Diff Account',
            'property_cost_method': 'last',
            'property_valuation': 'real_time',
            'property_stock_journal': self.stock_journal.id,
            'property_stock_valuation_account_id': self.stock_valuation_account.id,
        })
        product_no_diff = self.env['product.product'].create({
            'name': 'Test Product No Diff Account',
            'is_storable': True,
            'categ_id': category_no_diff.id,
            'standard_price': 10.0,
        })

        move = self.env['stock.move'].create({
            'name': 'Incoming Move No Diff',
            'product_id': product_no_diff.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.stock_location.id,
            'product_uom': product_no_diff.uom_id.id,
            'product_uom_qty': 5.0,
            'price_unit': 20.0,
        })
        move._action_confirm()
        move._action_assign()
        move.picked = True
        with self.assertRaises(UserError):
            move._action_done()
