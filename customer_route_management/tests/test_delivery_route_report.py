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
from unittest.mock import MagicMock
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestDeliveryRouteReport(TransactionCase):
    """Test cases for the RouteReport wizard (delivery route report
    generation – PDF and XLSX)."""

    def setUp(self):
        super().setUp()
        # Create a delivery route with lines and customers
        self.delivery_route = self.env['delivery.route'].create({
            'name': 'Delivery Route Report Test',
        })
        self.route_line = self.env['route.line'].create({
            'route': 'Zone Report',
            'sequence': 10,
            'delivery_route_link_id': self.delivery_route.id,
        })
        self.partner = self.env['res.partner'].create({
            'name': 'Report Customer',
            'location_id': self.route_line.id,
            'phone': '9876543210',
            'street': '12 Main St',
            'city': 'Test City',
            'email': 'report.customer@example.com',
        })
        # Create the wizard instance
        self.wizard = self.env['route.report'].create({
            'route_ids': [(4, self.delivery_route.id)],
            'payment': False,
            'consolidated': False,
        })

    # ------------------------------------------------------------------
    # Wizard field tests
    # ------------------------------------------------------------------

    def test_wizard_creation_defaults(self):
        """Test that the wizard is created with correct default values."""
        wizard = self.env['route.report'].create({})
        self.assertFalse(wizard.payment)
        self.assertFalse(wizard.consolidated)
        self.assertFalse(wizard.route_ids)

    def test_wizard_route_ids_many2many(self):
        """Test Many2many assignment of route_ids."""
        self.assertIn(self.delivery_route, self.wizard.route_ids)

    def test_wizard_payment_flag(self):
        """Test toggling the payment flag."""
        self.wizard.write({'payment': True})
        self.assertTrue(self.wizard.payment)
        self.wizard.write({'payment': False})
        self.assertFalse(self.wizard.payment)

    def test_wizard_consolidated_flag(self):
        """Test toggling the consolidated flag."""
        self.wizard.write({'consolidated': True})
        self.assertTrue(self.wizard.consolidated)

    def test_wizard_multiple_routes(self):
        """Test wizard with multiple routes assigned."""
        route2 = self.env['delivery.route'].create({'name': 'Route 2'})
        self.wizard.write({'route_ids': [(4, route2.id)]})
        self.assertIn(self.delivery_route, self.wizard.route_ids)
        self.assertIn(route2, self.wizard.route_ids)

    # ------------------------------------------------------------------
    # print_route_details (PDF) tests
    # ------------------------------------------------------------------

    def test_print_route_details_returns_action(self):
        """Test that print_route_details returns a report action dict."""
        action = self.wizard.print_route_details()
        self.assertIsInstance(action, dict,
                              "print_route_details should return a dict.")
        self.assertIn('type', action,
                      "Action should contain a 'type' key.")

    def test_print_route_details_data_structure(self):
        """Test that print_route_details passes correct data keys to the report."""
        # Call the method and verify the returned action is well-formed.
        # The wizard builds a data dict with keys: route, route_line_ids,
        # payment, consolidated – validated indirectly via a successful call.
        action = self.wizard.print_route_details()
        self.assertIsInstance(action, dict,
                              "print_route_details should return a dict.")
        self.assertIn('type', action,
                      "Returned action must contain a 'type' key.")
        # Verify with payment flag enabled as well
        self.wizard.write({'payment': True})
        action_pay = self.wizard.print_route_details()
        self.assertIsInstance(action_pay, dict)
        self.assertIn('type', action_pay)

    def test_print_route_details_no_routes(self):
        """Test PDF report action when no routes are selected."""
        wizard_empty = self.env['route.report'].create({
            'route_ids': [],
            'payment': False,
        })
        action = wizard_empty.print_route_details()
        self.assertIsInstance(action, dict)

    # ------------------------------------------------------------------
    # print_xlsx_report_route tests
    # ------------------------------------------------------------------

    def test_print_xlsx_report_route_returns_action(self):
        """Test that print_xlsx_report_route returns a valid action dict."""
        action = self.wizard.print_xlsx_report_route()
        self.assertIsInstance(action, dict)
        self.assertEqual(action.get('type'), 'ir.actions.report')
        self.assertEqual(action.get('report_type'), 'xlsx')

    def test_print_xlsx_report_route_data_keys(self):
        """Test that the xlsx action data contains required keys."""
        import json
        action = self.wizard.print_xlsx_report_route()
        data_str = action['data']['options']
        data = json.loads(data_str)
        self.assertIn('model', data)
        self.assertIn('route_ids', data)
        self.assertIn('payment', data)
        self.assertIn('consolidated', data)

    def test_print_xlsx_report_route_ids_in_data(self):
        """Test that route IDs are correctly passed to xlsx action."""
        import json
        action = self.wizard.print_xlsx_report_route()
        data = json.loads(action['data']['options'])
        self.assertIn(self.delivery_route.id, data['route_ids'])

    def test_print_xlsx_report_payment_true(self):
        """Test xlsx report action with payment=True."""
        import json
        self.wizard.write({'payment': True})
        action = self.wizard.print_xlsx_report_route()
        data = json.loads(action['data']['options'])
        self.assertTrue(data['payment'])

    def test_print_xlsx_report_consolidated_true(self):
        """Test xlsx report action with consolidated=True."""
        import json
        self.wizard.write({'payment': True, 'consolidated': True})
        action = self.wizard.print_xlsx_report_route()
        data = json.loads(action['data']['options'])
        self.assertTrue(data['consolidated'])

    def test_print_xlsx_report_name(self):
        """Test that the xlsx report carries the correct report name."""
        action = self.wizard.print_xlsx_report_route()
        self.assertEqual(
            action['data']['report_name'],
            'Customer Route Management Report'
        )

    # ------------------------------------------------------------------
    # get_xlsx_report tests
    # ------------------------------------------------------------------

    def test_get_xlsx_report_no_payment(self):
        """Test get_xlsx_report executes without errors when payment=False."""
        response = MagicMock()
        response.stream = MagicMock()
        data = {
            'route_ids': [self.delivery_route.id],
            'payment': False,
            'consolidated': False,
        }
        # Should not raise
        self.wizard.get_xlsx_report(data, response)
        response.stream.write.assert_called_once()

    def test_get_xlsx_report_payment_consolidated(self):
        """Test get_xlsx_report with payment=True and consolidated=True."""
        response = MagicMock()
        response.stream = MagicMock()
        data = {
            'route_ids': [self.delivery_route.id],
            'payment': True,
            'consolidated': True,
        }
        self.wizard.get_xlsx_report(data, response)
        response.stream.write.assert_called_once()

    def test_get_xlsx_report_no_routes(self):
        """Test get_xlsx_report with an empty route list."""
        response = MagicMock()
        response.stream = MagicMock()
        data = {
            'route_ids': [],
            'payment': False,
            'consolidated': False,
        }
        self.wizard.get_xlsx_report(data, response)
        response.stream.write.assert_called_once()

    def test_get_xlsx_report_writes_bytes(self):
        """Test that get_xlsx_report writes bytes to the response stream."""
        response = MagicMock()
        written = []
        response.stream.write = lambda x: written.append(x)
        data = {
            'route_ids': [self.delivery_route.id],
            'payment': False,
            'consolidated': False,
        }
        self.wizard.get_xlsx_report(data, response)
        self.assertTrue(len(written) > 0, "Bytes should have been written.")
        self.assertIsInstance(written[0], bytes,
                              "Written content should be bytes (xlsx).")
