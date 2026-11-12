# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(odoo@cybrosys.com)
#
#    This program is under the terms of the Odoo Proprietary License v1.0(OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the
#    Software or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NON INFRINGEMENT. IN NO EVENT SHALL
#    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,ARISING
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
###############################################################################
from unittest.mock import patch, MagicMock

from odoo.tests import tagged
from ..controller import saferpay as saferpay_mod
from ..controller.saferpay import SaferPayController
from .common import SaferpayCommon


@tagged('post_install', '-at_install')
class TestSaferpayController(SaferpayCommon):
    """Test suite for Saferpay checkout controller."""

    def setUp(self):
        super().setUp()
        self.controller = SaferPayController()
        self.tx = self.env['payment.transaction'].create({
            'amount': 25.0,
            'currency_id': self.currency.id,
            'provider_id': self.provider.id,
            'reference': 'TX-CTRL-TEST-001',
            'partner_id': self.partner.id,
            'payment_method_id': self.payment_method.id,
            'provider_reference': 'token_init_ctrl_01',
        })
        self.mock_request = MagicMock()
        self.mock_request.env = self.env
        self.mock_request.session = {'saferpay_data': {}}
        self.mock_request.redirect.side_effect = lambda url: f"REDIRECT:{url}"
        self.orig_request = saferpay_mod.request
        saferpay_mod.request = self.mock_request

    def tearDown(self):
        saferpay_mod.request = self.orig_request
        super().tearDown()

    def _get_response_text(self, response):
        if hasattr(response, 'get_data'):
            return response.get_data(as_text=True)
        return str(response)

    @patch('requests.post')
    def test_return_from_checkout_success(self, mock_post):
        """Ensure successful return asserts payment and records transaction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Transaction': {
                'Status': 'CAPTURED',
                'Id': 'SP_CTRL_CAPTURED_999',
                'Amount': {
                    'Value': '2500',
                    'CurrencyCode': self.currency.name,
                }
            }
        }
        mock_post.return_value = mock_response

        response = self.controller.saferpay_return_from_checkout(
            tx_ref=self.tx.reference,
            token='token_init_ctrl_01',
        )

        mock_post.assert_called_once()
        self.assertEqual(self._get_response_text(response), "REDIRECT:/payment/status")
        # Process the queued payment data in Odoo 20
        payment_data = self.env['payment.data'].search([('transaction_id', '=', self.tx.id)], limit=1)
        self.assertTrue(payment_data, "Payment data record should have been queued by _record().")
        self.tx.with_context(payment_safe_write=True)._process(payment_data.payload)
        self.assertEqual(self.tx.state, 'done')
        self.assertEqual(self.tx.provider_reference, 'SP_CTRL_CAPTURED_999')

    @patch('requests.post')
    def test_return_from_checkout_assertion_failure(self, mock_post):
        """Ensure failed assert sets transaction to error state."""
        mock_post.side_effect = Exception("Connection timeout to Saferpay")

        response = self.controller.saferpay_return_from_checkout(
            tx_ref=self.tx.reference,
            token='token_init_ctrl_01',
        )

        self.assertEqual(self._get_response_text(response), "REDIRECT:/payment/status")
        self.assertEqual(self.tx.state, 'error')
        self.assertIn("SaferPay assertion error", self.tx.state_message)

    def test_return_from_checkout_fallback_redirect(self):
        """Ensure missing transaction or token falls back to checkout redirect."""
        self.mock_request.session = {}

        response = self.controller.saferpay_return_from_checkout(
            tx_ref='INVALID_TX_REF',
        )

        self.assertEqual(self._get_response_text(response), "REDIRECT:/shop/payment")

    def test_return_from_checkout_session_fallback(self):
        """Ensure return fallback uses session when tx_ref is not in parameters."""
        self.mock_request.session = {
            'saferpay_data': {
                'tx_ref': self.tx.reference,
                'token': 'token_init_ctrl_01',
            }
        }
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'Transaction': {
                    'Status': 'AUTHORIZED',
                    'Id': 'SP_CTRL_SESSION_01',
                    'Amount': {'Value': '2500', 'CurrencyCode': self.currency.name}
                }
            }
            mock_post.return_value = mock_response

            response = self.controller.saferpay_return_from_checkout()
            self.assertEqual(self._get_response_text(response), "REDIRECT:/payment/status")

    def test_return_from_checkout_monitored_tx_fallback(self):
        """Ensure monitored transaction fallback is used when no token is passed."""
        self.mock_request.session = {
            '__payment_monitored_tx_id__': self.tx.id,
        }
        self.tx.with_context(payment_safe_write=True).provider_reference = False

        response = self.controller.saferpay_return_from_checkout()
        self.assertEqual(self._get_response_text(response), "REDIRECT:/payment/status")
