# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Henna Mehjabin (odoo@cybrosys.com)
#
#    This program is under the terms of the Odoo Proprietary License v1.0
#    (OPL-1) It is forbidden to publish, distribute, sublicense, or
#    sell copies of the Software or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
#    CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT
#    OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR
#    THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
###############################################################################
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestResPartner(TransactionCase):
    """Test cases for the ResPartner extension in customer_route_management:
    the location_id / sequence fields and the get_all_dues() method."""

    def setUp(self):
        super().setUp()
        # Create a delivery route and route line
        self.delivery_route = self.env['delivery.route'].create({
            'name': 'Partner Test Route',
        })
        self.route_line = self.env['route.line'].create({
            'route': 'Partner Zone',
            'sequence': 10,
            'delivery_route_link_id': self.delivery_route.id,
        })
        # Create a customer partner linked to the route line
        self.partner = self.env['res.partner'].create({
            'name': 'Partner Test Customer',
            'customer_rank': 1,
            'location_id': self.route_line.id,
        })

    # ------------------------------------------------------------------
    # Field tests
    # ------------------------------------------------------------------

    def test_partner_location_id_field(self):
        """Test that location_id field links to the correct route line."""
        self.assertEqual(
            self.partner.location_id, self.route_line,
            "Partner's location_id should be the assigned route line."
        )

    def test_partner_sequence_default(self):
        """Test that sequence defaults to 10 for a new partner."""
        partner = self.env['res.partner'].create({'name': 'Seq Default Test'})
        self.assertEqual(partner.sequence, 10,
                         "Default sequence should be 10.")

    def test_partner_sequence_custom(self):
        """Test setting a custom sequence value."""
        self.partner.write({'sequence': 25})
        self.assertEqual(self.partner.sequence, 25)

    def test_partner_location_id_no_route(self):
        """Test that a partner can exist without a location_id."""
        partner = self.env['res.partner'].create({'name': 'No Route Partner'})
        self.assertFalse(partner.location_id)

    def test_partner_location_id_update(self):
        """Test updating location_id to a different route line."""
        new_line = self.env['route.line'].create({
            'route': 'Zone New',
            'delivery_route_link_id': self.delivery_route.id,
        })
        self.partner.write({'location_id': new_line.id})
        self.assertEqual(self.partner.location_id, new_line)

    def test_partner_appears_in_route_line_customers(self):
        """Test that assigning location_id makes partner appear in
        cust_list_ids of the route line."""
        self.assertIn(self.partner, self.route_line.cust_list_ids)

    def test_multiple_partners_same_route_line(self):
        """Test that multiple partners can be assigned to the same route line."""
        p2 = self.env['res.partner'].create({
            'name': 'Partner B',
            'location_id': self.route_line.id,
        })
        p3 = self.env['res.partner'].create({
            'name': 'Partner C',
            'location_id': self.route_line.id,
        })
        self.assertIn(p2, self.route_line.cust_list_ids)
        self.assertIn(p3, self.route_line.cust_list_ids)

    # ------------------------------------------------------------------
    # get_all_dues() tests
    # ------------------------------------------------------------------

    def test_get_all_dues_returns_list(self):
        """Test that get_all_dues returns a list."""
        result = self.partner.get_all_dues()
        self.assertIsInstance(result, list,
                              "get_all_dues should return a list.")

    def test_get_all_dues_empty_for_no_invoices(self):
        """Test that get_all_dues returns an empty list for a customer
        with no posted invoices with outstanding balance."""
        result = self.partner.get_all_dues()
        self.assertEqual(result, [],
                         "New customer should have no dues.")

    def test_get_all_dues_with_posted_invoice(self):
        """Test that get_all_dues returns invoice data for a customer
        with a posted invoice that has an outstanding amount."""
        # Create a journal for testing
        journal = self.env['account.journal'].search(
            [('type', '=', 'sale')], limit=1
        )
        if not journal:
            self.skipTest("No sale journal found – skipping invoice test.")

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': journal.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Test Service',
                'quantity': 1,
                'price_unit': 500.0,
            })],
        })
        invoice.action_post()

        dues = self.partner.get_all_dues()
        self.assertIsInstance(dues, list)
        # The invoice should appear in dues since it has a residual balance
        self.assertTrue(len(dues) > 0,
                        "Posted invoice with balance should appear in dues.")
        names = [d['name'] for d in dues]
        self.assertIn(invoice.name, names,
                      "Invoice name should be in dues list.")

    def test_get_all_dues_excludes_draft_invoices(self):
        """Test that get_all_dues does NOT return draft invoices."""
        journal = self.env['account.journal'].search(
            [('type', '=', 'sale')], limit=1
        )
        if not journal:
            self.skipTest("No sale journal found – skipping draft invoice test.")

        draft_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': journal.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Draft Service',
                'quantity': 1,
                'price_unit': 200.0,
            })],
        })
        # Invoice stays in draft – not posted
        dues = self.partner.get_all_dues()
        names = [d['name'] for d in dues]
        self.assertNotIn(draft_invoice.name, names,
                         "Draft invoice should NOT appear in dues.")

    def test_get_all_dues_dict_keys(self):
        """Test that each due entry has the required dict keys."""
        journal = self.env['account.journal'].search(
            [('type', '=', 'sale')], limit=1
        )
        if not journal:
            self.skipTest("No sale journal found.")

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': journal.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Key Test Service',
                'quantity': 1,
                'price_unit': 300.0,
            })],
        })
        invoice.action_post()
        dues = self.partner.get_all_dues()
        if dues:
            entry = dues[0]
            self.assertIn('name', entry)
            self.assertIn('invoice_date_due', entry)
            self.assertIn('amount_residual_signed', entry)

    def test_get_all_dues_for_partner_with_children(self):
        """Test that get_all_dues also considers invoices for child
        contacts of the partner."""
        child = self.env['res.partner'].create({
            'name': 'Child Contact',
            'parent_id': self.partner.id,
        })
        journal = self.env['account.journal'].search(
            [('type', '=', 'sale')], limit=1
        )
        if not journal:
            self.skipTest("No sale journal found.")

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': child.id,
            'journal_id': journal.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Child Service',
                'quantity': 1,
                'price_unit': 150.0,
            })],
        })
        invoice.action_post()
        dues = self.partner.get_all_dues()
        self.assertTrue(len(dues) > 0,
                        "Dues from child contacts should be included.")
