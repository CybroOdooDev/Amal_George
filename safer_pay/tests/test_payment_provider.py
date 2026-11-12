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
from odoo.tests import tagged
from .common import SaferpayCommon


@tagged('post_install', '-at_install')
class TestPaymentProvider(SaferpayCommon):
    """Test suite for Saferpay payment provider model."""

    def test_default_payment_method_codes(self):
        """Ensure default payment method codes returns 'saferpay'."""
        self.assertEqual(
            self.provider._get_default_payment_method_codes(),
            {'saferpay'},
            "Saferpay provider should return {'saferpay'} as default payment method code."
        )

    def test_default_payment_method_codes_non_saferpay(self):
        """Ensure other providers delegate to super()."""
        other_provider = self.env['payment.provider'].create({
            'name': 'Other Provider',
            'code': 'custom',
            'is_live': False,
        })
        res = other_provider._get_default_payment_method_codes()
        self.assertIsInstance(res, (set, list))

    def test_saferpay_get_api_url_test_mode(self):
        """Ensure test mode resolves to Saferpay test API endpoint."""
        self.provider.is_live = False
        self.assertEqual(
            self.provider._saferpay_get_api_url(),
            'https://test.saferpay.com/api',
            "When is_live is False, API URL should point to https://test.saferpay.com/api"
        )

    def test_saferpay_get_api_url_enabled_mode(self):
        """Ensure live mode resolves to Saferpay production API endpoint."""
        self.provider.is_live = True
        self.assertEqual(
            self.provider._saferpay_get_api_url(),
            'https://www.saferpay.com/api',
            "When is_live is True, API URL should point to https://www.saferpay.com/api"
        )

    def test_saferpay_credentials_fields(self):
        """Ensure credentials fields can be set and read accurately."""
        self.assertEqual(self.provider.customer, '287995')
        self.assertEqual(self.provider.terminal, '17781432')
        self.assertEqual(self.provider.username, 'API_287995_test')
        self.assertEqual(self.provider.password, 'TestPassword123!')

