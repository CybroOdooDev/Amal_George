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
class TestCustomerRouteManagement(TransactionCase):
    """Test cases for customer_route_management module covering
    DeliveryRoute and RouteLine models."""

    def setUp(self):
        super().setUp()
        # Create a delivery route for testing
        self.delivery_route = self.env['delivery.route'].create({
            'name': 'Test Route Alpha',
        })
        # Create a route line linked to the delivery route
        self.route_line = self.env['route.line'].create({
            'route': 'Zone A',
            'sequence': 5,
            'delivery_route_link_id': self.delivery_route.id,
        })

    # ------------------------------------------------------------------
    # DeliveryRoute model tests
    # ------------------------------------------------------------------

    def test_delivery_route_creation(self):
        """Test that a DeliveryRoute record is created with correct values."""
        self.assertEqual(self.delivery_route.name, 'Test Route Alpha')
        self.assertEqual(
            self.delivery_route.company_id, self.env.company,
            "Company should default to the current company."
        )

    def test_delivery_route_default_company(self):
        """Test that company_id defaults to the current company."""
        route = self.env['delivery.route'].create({'name': 'Route Beta'})
        self.assertEqual(route.company_id, self.env.company)

    def test_delivery_route_name_update(self):
        """Test updating the name of a delivery route."""
        self.delivery_route.write({'name': 'Updated Route Name'})
        self.assertEqual(self.delivery_route.name, 'Updated Route Name')

    def test_delivery_route_multiple_routes(self):
        """Test creating multiple delivery routes and searching them."""
        route2 = self.env['delivery.route'].create({'name': 'Route Gamma'})
        route3 = self.env['delivery.route'].create({'name': 'Route Delta'})
        routes = self.env['delivery.route'].search(
            [('name', 'in', ['Route Gamma', 'Route Delta'])]
        )
        self.assertEqual(len(routes), 2)
        self.assertIn(route2, routes)
        self.assertIn(route3, routes)

    def test_delivery_route_has_route_lines(self):
        """Test that route_line_ids One2many is populated correctly."""
        self.assertIn(
            self.route_line,
            self.delivery_route.route_line_ids,
            "Route line should appear in delivery route's route_line_ids."
        )

    def test_delivery_route_multiple_lines(self):
        """Test a delivery route with multiple route lines."""
        line2 = self.env['route.line'].create({
            'route': 'Zone B',
            'sequence': 10,
            'delivery_route_link_id': self.delivery_route.id,
        })
        line3 = self.env['route.line'].create({
            'route': 'Zone C',
            'sequence': 15,
            'delivery_route_link_id': self.delivery_route.id,
        })
        self.assertEqual(len(self.delivery_route.route_line_ids), 3)
        self.assertIn(line2, self.delivery_route.route_line_ids)
        self.assertIn(line3, self.delivery_route.route_line_ids)

    def test_delivery_route_unlink(self):
        """Test that a delivery route can be deleted."""
        route_id = self.delivery_route.id
        self.delivery_route.unlink()
        remaining = self.env['delivery.route'].search(
            [('id', '=', route_id)]
        )
        self.assertFalse(remaining, "Deleted route should not be found.")

    # ------------------------------------------------------------------
    # RouteLine model tests
    # ------------------------------------------------------------------

    def test_route_line_creation(self):
        """Test that a RouteLine record is created with correct values."""
        self.assertEqual(self.route_line.route, 'Zone A')
        self.assertEqual(self.route_line.sequence, 5)
        self.assertEqual(
            self.route_line.delivery_route_link_id, self.delivery_route
        )

    def test_route_line_default_company(self):
        """Test that company_id defaults to the current company on route line."""
        self.assertEqual(self.route_line.company_id, self.env.company)

    def test_route_line_sequence_ordering(self):
        """Test that route lines are ordered by sequence."""
        line_low = self.env['route.line'].create({
            'route': 'Seq 1',
            'sequence': 1,
            'delivery_route_link_id': self.delivery_route.id,
        })
        line_high = self.env['route.line'].create({
            'route': 'Seq 20',
            'sequence': 20,
            'delivery_route_link_id': self.delivery_route.id,
        })
        lines = self.env['route.line'].search(
            [('delivery_route_link_id', '=', self.delivery_route.id)]
        )
        sequences = lines.mapped('sequence')
        self.assertEqual(sequences, sorted(sequences),
                         "Route lines should be sorted by sequence.")

    def test_route_line_update_route(self):
        """Test updating the route field of a route line."""
        self.route_line.write({'route': 'Zone A Updated'})
        self.assertEqual(self.route_line.route, 'Zone A Updated')

    def test_route_line_cust_list_ids(self):
        """Test that customers (res.partner) linked via location_id appear
        in cust_list_ids."""
        partner = self.env['res.partner'].create({
            'name': 'Test Customer Route',
            'location_id': self.route_line.id,
        })
        self.assertIn(
            partner, self.route_line.cust_list_ids,
            "Partner should be listed under route line cust_list_ids."
        )

    def test_route_line_multiple_customers(self):
        """Test multiple customers linked to a single route line."""
        partner1 = self.env['res.partner'].create({
            'name': 'Customer One',
            'location_id': self.route_line.id,
        })
        partner2 = self.env['res.partner'].create({
            'name': 'Customer Two',
            'location_id': self.route_line.id,
        })
        self.assertEqual(len(self.route_line.cust_list_ids), 2)
        self.assertIn(partner1, self.route_line.cust_list_ids)
        self.assertIn(partner2, self.route_line.cust_list_ids)

    def test_route_line_rec_name(self):
        """Test that _rec_name is 'route', so display_name returns route value."""
        self.assertEqual(self.route_line.display_name, 'Zone A')

    def test_route_line_without_delivery_route(self):
        """Test creating a standalone route line (no delivery route link)."""
        standalone = self.env['route.line'].create({'route': 'Standalone Zone'})
        self.assertFalse(standalone.delivery_route_link_id)

    def test_route_line_unlink(self):
        """Test that a route line can be deleted."""
        line_id = self.route_line.id
        self.route_line.unlink()
        remaining = self.env['route.line'].search([('id', '=', line_id)])
        self.assertFalse(remaining, "Deleted route line should not be found.")
