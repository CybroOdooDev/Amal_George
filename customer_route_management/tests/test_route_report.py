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
import json
from unittest.mock import MagicMock
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestRouteReport(TransactionCase):
    """Test cases for the RouteReport wizard focusing on the full
    integration between wizard fields, PDF action, XLSX action, and
    the XLSX workbook generation (get_xlsx_report)."""

    def setUp(self):
        super().setUp()
        # Create two delivery routes with route lines and customers
        self.route_a = self.env['delivery.route'].create({'name': 'Route A'})
        self.route_b = self.env['delivery.route'].create({'name': 'Route B'})

        self.line_a1 = self.env['route.line'].create({
            'route': 'Zone A1',
            'sequence': 5,
            'delivery_route_link_id': self.route_a.id,
        })
        self.line_a2 = self.env['route.line'].create({
            'route': 'Zone A2',
            'sequence': 10,
            'delivery_route_link_id': self.route_a.id,
        })
        self.line_b1 = self.env['route.line'].create({
            'route': 'Zone B1',
            'sequence': 5,
            'delivery_route_link_id': self.route_b.id,
        })

        self.cust1 = self.env['res.partner'].create({
            'name': 'Customer Alpha',
            'phone': '1111111111',
            'location_id': self.line_a1.id,
            'street': '1 Alpha St',
            'city': 'Alpha City',
        })
        self.cust2 = self.env['res.partner'].create({
            'name': 'Customer Beta',
            'phone': '2222222222',
            'location_id': self.line_b1.id,
            'street': '2 Beta Ave',
            'city': 'Beta Town',
        })

        # Base wizard
        self.wizard = self.env['route.report'].create({
            'route_ids': [(6, 0, [self.route_a.id])],
            'payment': False,
            'consolidated': False,
        })

    # ------------------------------------------------------------------
    # Wizard creation / field tests
    # ------------------------------------------------------------------

    def test_wizard_creation(self):
        """Test basic wizard creation."""
        self.assertTrue(self.wizard.id)
        self.assertIn(self.route_a, self.wizard.route_ids)

    def test_wizard_empty_creation(self):
        """Test wizard created with no arguments uses safe defaults."""
        empty = self.env['route.report'].create({})
        self.assertFalse(empty.payment)
        self.assertFalse(empty.consolidated)
        self.assertEqual(len(empty.route_ids), 0)

    def test_wizard_many2many_multiple_routes(self):
        """Test assigning multiple routes to the wizard."""
        self.wizard.write({
            'route_ids': [(6, 0, [self.route_a.id, self.route_b.id])]
        })
        self.assertIn(self.route_a, self.wizard.route_ids)
        self.assertIn(self.route_b, self.wizard.route_ids)
        self.assertEqual(len(self.wizard.route_ids), 2)

    def test_wizard_payment_and_consolidated_flags(self):
        """Test toggling payment and consolidated flags."""
        self.wizard.write({'payment': True, 'consolidated': True})
        self.assertTrue(self.wizard.payment)
        self.assertTrue(self.wizard.consolidated)
        self.wizard.write({'payment': False, 'consolidated': False})
        self.assertFalse(self.wizard.payment)
        self.assertFalse(self.wizard.consolidated)

    # ------------------------------------------------------------------
    # print_route_details (PDF) tests
    # ------------------------------------------------------------------

    def test_print_route_details_returns_dict(self):
        """Test that PDF action returns a dict."""
        action = self.wizard.print_route_details()
        self.assertIsInstance(action, dict)

    def test_print_route_details_type_key(self):
        """Test that the returned action contains a 'type' key."""
        action = self.wizard.print_route_details()
        self.assertIn('type', action)

    def test_print_route_details_with_payment(self):
        """Test PDF action when payment=True."""
        self.wizard.write({'payment': True})
        action = self.wizard.print_route_details()
        self.assertIsInstance(action, dict)

    def test_print_route_details_with_consolidated(self):
        """Test PDF action when payment=True and consolidated=True."""
        self.wizard.write({'payment': True, 'consolidated': True})
        action = self.wizard.print_route_details()
        self.assertIsInstance(action, dict)

    def test_print_route_details_two_routes(self):
        """Test PDF action with two routes."""
        self.wizard.write({
            'route_ids': [(6, 0, [self.route_a.id, self.route_b.id])]
        })
        action = self.wizard.print_route_details()
        self.assertIsInstance(action, dict)

    def test_print_route_details_empty_routes(self):
        """Test PDF action when route_ids is empty."""
        self.wizard.write({'route_ids': [(5,)]})
        action = self.wizard.print_route_details()
        self.assertIsInstance(action, dict)

    # ------------------------------------------------------------------
    # print_xlsx_report_route tests
    # ------------------------------------------------------------------

    def test_print_xlsx_report_returns_action(self):
        """Test that XLSX action dict is returned."""
        action = self.wizard.print_xlsx_report_route()
        self.assertIsInstance(action, dict)

    def test_print_xlsx_report_type_is_report(self):
        """Test action type is ir.actions.report."""
        action = self.wizard.print_xlsx_report_route()
        self.assertEqual(action['type'], 'ir.actions.report')

    def test_print_xlsx_report_report_type_xlsx(self):
        """Test report_type is 'xlsx'."""
        action = self.wizard.print_xlsx_report_route()
        self.assertEqual(action['report_type'], 'xlsx')

    def test_print_xlsx_report_output_format(self):
        """Test output_format in data is 'xlsx'."""
        action = self.wizard.print_xlsx_report_route()
        self.assertEqual(action['data']['output_format'], 'xlsx')

    def test_print_xlsx_report_options_json_valid(self):
        """Test that 'options' in data is valid JSON."""
        action = self.wizard.print_xlsx_report_route()
        try:
            data = json.loads(action['data']['options'])
        except (ValueError, KeyError) as e:
            self.fail(f"options is not valid JSON: {e}")
        self.assertIsInstance(data, dict)

    def test_print_xlsx_report_options_model(self):
        """Test that options contains correct model name."""
        action = self.wizard.print_xlsx_report_route()
        data = json.loads(action['data']['options'])
        self.assertEqual(data['model'], 'route.report')

    def test_print_xlsx_report_options_route_ids(self):
        """Test that options contains the correct route IDs."""
        action = self.wizard.print_xlsx_report_route()
        data = json.loads(action['data']['options'])
        self.assertIn(self.route_a.id, data['route_ids'])

    def test_print_xlsx_report_options_payment_false(self):
        """Test that options correctly reflects payment=False."""
        action = self.wizard.print_xlsx_report_route()
        data = json.loads(action['data']['options'])
        self.assertFalse(data['payment'])

    def test_print_xlsx_report_options_payment_true(self):
        """Test that options correctly reflects payment=True."""
        self.wizard.write({'payment': True})
        action = self.wizard.print_xlsx_report_route()
        data = json.loads(action['data']['options'])
        self.assertTrue(data['payment'])

    def test_print_xlsx_report_options_consolidated_false(self):
        """Test that options correctly reflects consolidated=False."""
        action = self.wizard.print_xlsx_report_route()
        data = json.loads(action['data']['options'])
        self.assertFalse(data['consolidated'])

    def test_print_xlsx_report_options_consolidated_true(self):
        """Test that options correctly reflects consolidated=True."""
        self.wizard.write({'payment': True, 'consolidated': True})
        action = self.wizard.print_xlsx_report_route()
        data = json.loads(action['data']['options'])
        self.assertTrue(data['consolidated'])

    # ------------------------------------------------------------------
    # get_xlsx_report tests
    # ------------------------------------------------------------------

    def _make_response(self):
        """Helper to create a mock HTTP response."""
        response = MagicMock()
        response.stream = MagicMock()
        written = []
        response.stream.write = lambda x: written.append(x)
        response._written = written
        return response

    def test_get_xlsx_report_basic(self):
        """Test that get_xlsx_report runs without errors and writes output."""
        response = self._make_response()
        data = {
            'route_ids': [self.route_a.id],
            'payment': False,
            'consolidated': False,
        }
        self.wizard.get_xlsx_report(data, response)
        self.assertTrue(len(response._written) > 0,
                        "XLSX content should be written to stream.")

    def test_get_xlsx_report_output_is_bytes(self):
        """Test that written content is bytes."""
        response = self._make_response()
        data = {
            'route_ids': [self.route_a.id],
            'payment': False,
            'consolidated': False,
        }
        self.wizard.get_xlsx_report(data, response)
        self.assertIsInstance(response._written[0], bytes)

    def test_get_xlsx_report_payment_no_consolidated(self):
        """Test XLSX with payment=True and consolidated=False (detail mode)."""
        response = self._make_response()
        data = {
            'route_ids': [self.route_a.id],
            'payment': True,
            'consolidated': False,
        }
        self.wizard.get_xlsx_report(data, response)
        self.assertTrue(len(response._written) > 0)

    def test_get_xlsx_report_payment_and_consolidated(self):
        """Test XLSX with payment=True and consolidated=True (summary mode)."""
        response = self._make_response()
        data = {
            'route_ids': [self.route_a.id],
            'payment': True,
            'consolidated': True,
        }
        self.wizard.get_xlsx_report(data, response)
        self.assertTrue(len(response._written) > 0)

    def test_get_xlsx_report_multiple_routes(self):
        """Test XLSX generation with multiple routes."""
        response = self._make_response()
        data = {
            'route_ids': [self.route_a.id, self.route_b.id],
            'payment': False,
            'consolidated': False,
        }
        self.wizard.get_xlsx_report(data, response)
        self.assertTrue(len(response._written) > 0)

    def test_get_xlsx_report_empty_route_list(self):
        """Test XLSX generation with no routes (empty list)."""
        response = self._make_response()
        data = {
            'route_ids': [],
            'payment': False,
            'consolidated': False,
        }
        self.wizard.get_xlsx_report(data, response)
        # Should still write a valid (empty) xlsx workbook
        self.assertTrue(len(response._written) > 0)

    def test_get_xlsx_report_route_with_multiple_lines(self):
        """Test XLSX with a route that has multiple route lines."""
        response = self._make_response()
        data = {
            'route_ids': [self.route_a.id],  # route_a has line_a1, line_a2
            'payment': False,
            'consolidated': False,
        }
        self.wizard.get_xlsx_report(data, response)
        self.assertIsInstance(response._written[0], bytes)
