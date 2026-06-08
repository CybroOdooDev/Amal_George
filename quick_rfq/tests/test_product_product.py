# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestProductProduct(TransactionCase):
    """Test cases for the ProductProduct model extension in quick_rfq."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create products with specific standard_price
        cls.product_1 = cls.env['product.product'].create({
            'name': 'Test Product 1',
            'standard_price': 15.0,
            'type': 'consu',
        })
        cls.product_2 = cls.env['product.product'].create({
            'name': 'Test Product 2',
            'standard_price': 25.0,
            'type': 'consu',
        })

    def test_action_create_rfq(self):
        """Test action_create_rfq creates a wizard with correct lines."""
        products = self.product_1 | self.product_2
        action = products.action_create_rfq()

        # Check action properties
        self.assertEqual(action.get('type'), 'ir.actions.act_window')
        self.assertEqual(action.get('res_model'), 'product.rfq')
        self.assertEqual(action.get('view_mode'), 'form')
        self.assertEqual(action.get('target'), 'new')

        # Check wizard record and lines
        wizard_id = action.get('res_id')
        self.assertTrue(wizard_id, "Wizard ID should be set in action result.")
        wizard = self.env['product.rfq'].browse(wizard_id)
        self.assertTrue(wizard.exists(), "Wizard record should exist in database.")

        self.assertEqual(len(wizard.rfq_line_ids), 2, "Wizard should have 2 product lines.")

        line_1 = wizard.rfq_line_ids.filtered(lambda l: l.product_id == self.product_1)
        self.assertTrue(line_1, "Line for Product 1 should exist.")
        self.assertEqual(line_1.product_qty, 1.0)
        self.assertEqual(line_1.price_unit, 15.0)

        line_2 = wizard.rfq_line_ids.filtered(lambda l: l.product_id == self.product_2)
        self.assertTrue(line_2, "Line for Product 2 should exist.")
        self.assertEqual(line_2.product_qty, 1.0)
        self.assertEqual(line_2.price_unit, 25.0)
