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
import json
from unittest.mock import patch, MagicMock

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from .common import SaferpayCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(SaferpayCommon):
    """Test suite for Saferpay payment transaction model."""

    def setUp(self):
        super().setUp()
        self.tx = self.env['payment.transaction'].create({
            'amount': 50.0,
            'currency_id': self.currency.id,
            'provider_id': self.provider.id,
            'reference': 'TX-SAFERPAY-TEST-001',
            'partner_id': self.partner.id,
            'payment_method_id': self.payment_method.id,
        })

    def test_rendering_values_missing_credentials(self):
        """Ensure ValidationError is raised when credentials are missing."""
        self.provider.username = False
        with self.assertRaises(ValidationError):
            self.tx._get_specific_rendering_values({
                'amount': 50.0,
                'currency_id': self.currency.id,
            })

    @patch('requests.post')
    def test_rendering_values_success(self, mock_post):
        """Ensure payment page initialization succeeds and sets token and redirect URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Token': 'token_test_123456',
            'RedirectUrl': 'https://test.saferpay.com/Payment/v1/PaymentPage/token_test_123456',
        }
        mock_post.return_value = mock_response

        res = self.tx._get_specific_rendering_values({
            'amount': 50.0,
            'currency_id': self.currency.id,
        })

        self.assertIn('url', res)
        self.assertEqual(res['url'], 'https://test.saferpay.com/Payment/v1/PaymentPage/token_test_123456')
        self.assertEqual(self.tx.provider_reference, 'token_test_123456')

        # Verify payload sent to Saferpay Initialize API
        mock_post.assert_called_once()
        sent_args, sent_kwargs = mock_post.call_args
        self.assertIn('https://test.saferpay.com/api/Payment/v1/PaymentPage/Initialize', sent_args[0])
        payload = json.loads(sent_kwargs['data'])
        self.assertEqual(payload['RequestHeader']['CustomerId'], '287995')
        self.assertEqual(payload['TerminalId'], '17781432')
        self.assertEqual(payload['Payment']['Amount']['Value'], '5000')

    @patch('requests.post')
    def test_rendering_values_api_error(self, mock_post):
        """Ensure API errors raise ValidationError with error details."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'ErrorMessage': 'Invalid Terminal ID',
        }
        mock_post.return_value = mock_response

        with self.assertRaises(ValidationError):
            self.tx._get_specific_rendering_values({
                'amount': 50.0,
                'currency_id': self.currency.id,
            })

    def test_search_by_reference(self):
        """Ensure transaction can be searched by order id, reference, or token."""
        # Search by OrderId (tx.id)
        found_tx = self.env['payment.transaction']._search_by_reference('saferpay', {'OrderId': self.tx.id})
        self.assertEqual(found_tx, self.tx)

        # Search by reference
        found_tx = self.env['payment.transaction']._search_by_reference('saferpay', {'reference': self.tx.reference})
        self.assertEqual(found_tx, self.tx)

        # Search by Token
        self.tx.with_context(payment_safe_write=True).provider_reference = 'token_abc_xyz'
        found_tx = self.env['payment.transaction']._search_by_reference('saferpay', {'Token': 'token_abc_xyz'})
        self.assertEqual(found_tx, self.tx)

        # Search non-existing reference raises ValidationError
        with self.assertRaises(ValidationError):
            self.env['payment.transaction']._search_by_reference('saferpay', {'reference': 'NON_EXISTENT'})

    def test_extract_amount_data(self):
        """Ensure minor currency units are converted correctly to major units."""
        payment_data = {
            'Transaction': {
                'Amount': {
                    'Value': '5000',
                    'CurrencyCode': self.currency.name,
                }
            }
        }
        extracted = self.tx._extract_amount_data(payment_data)
        self.assertIsNotNone(extracted)
        self.assertEqual(extracted['amount'], 50.0)
        self.assertEqual(extracted['currency_code'], self.currency.name)

    def test_apply_updates_authorized_and_captured(self):
        """Ensure AUTHORIZED and CAPTURED statuses mark the transaction done."""
        payment_data = {
            'Transaction': {
                'Status': 'CAPTURED',
                'Id': 'SP_TX_12345',
            }
        }
        self.tx.with_context(payment_safe_write=True)._apply_updates(payment_data)
        self.assertEqual(self.tx.state, 'done')
        self.assertEqual(self.tx.provider_reference, 'SP_TX_12345')

    def test_apply_updates_pending(self):
        """Ensure PENDING status marks the transaction as pending."""
        payment_data = {
            'Transaction': {
                'Status': 'PENDING',
                'Id': 'SP_TX_PENDING_01',
            }
        }
        self.tx.with_context(payment_safe_write=True)._apply_updates(payment_data)
        self.assertEqual(self.tx.state, 'pending')

    def test_apply_updates_canceled(self):
        """Ensure CANCELED status cancels the transaction."""
        payment_data = {
            'Transaction': {
                'Status': 'CANCELED',
                'Id': 'SP_TX_CANCEL_01',
            }
        }
        self.tx.with_context(payment_safe_write=True)._apply_updates(payment_data)
        self.assertEqual(self.tx.state, 'cancel')

    def test_apply_updates_failed(self):
        """Ensure FAILED status marks the transaction as error."""
        payment_data = {
            'Transaction': {
                'Status': 'FAILED',
                'Id': 'SP_TX_FAIL_01',
            }
        }
        self.tx.with_context(payment_safe_write=True)._apply_updates(payment_data)
        self.assertEqual(self.tx.state, 'error')

    def test_apply_updates_error_name(self):
        """Ensure error name or message in payment data marks transaction as error."""
        payment_data = {
            'ErrorName': 'CARD_DECLINED',
            'ErrorMessage': 'Card limit exceeded',
        }
        self.tx.with_context(payment_safe_write=True)._apply_updates(payment_data)
        self.assertEqual(self.tx.state, 'error')

    def test_apply_updates_unhandled_status(self):
        """Ensure unknown status marks transaction as error."""
        payment_data = {
            'Transaction': {
                'Status': 'UNKNOWN_STATUS_XYZ',
            }
        }
        self.tx.with_context(payment_safe_write=True)._apply_updates(payment_data)
        self.assertEqual(self.tx.state, 'error')

    def test_sanitize_message_none(self):
        """Ensure _sanitize_message returns None when message is None."""
        self.assertIsNone(self.tx._sanitize_message(None))

    def test_extract_amount_data_none(self):
        """Ensure _extract_amount_data returns None if Amount is missing."""
        self.assertIsNone(self.tx._extract_amount_data({}))

    def test_non_saferpay_methods_delegation(self):
        """Ensure non-saferpay transactions delegate to super()."""
        other_provider = self.env['payment.provider'].create({
            'name': 'Other Provider 2',
            'code': 'custom',
            'is_live': False,
        })
        other_method = self.env['payment.method'].create({
            'name': 'Other Method',
            'code': 'other',
            'provider_id': other_provider.id,
            'active': True,
        })
        other_tx = self.env['payment.transaction'].create({
            'amount': 10.0,
            'currency_id': self.currency.id,
            'provider_id': other_provider.id,
            'reference': 'TX-OTHER-001',
            'partner_id': self.partner.id,
            'payment_method_id': other_method.id,
        })
        res = other_tx._get_specific_rendering_values({'amount': 10.0})
        self.assertIsInstance(res, dict)
        self.assertIsNone(other_tx._extract_amount_data({}))
        other_tx.with_context(payment_safe_write=True)._apply_updates({})

