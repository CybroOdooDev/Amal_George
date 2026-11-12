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
import base64
import json
import logging
import requests

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SaferPayController(http.Controller):
    """For managing payments with safer pay"""

    @http.route('/saferpay/payment/status', type='http', auth='public', csrf=False)
    def saferpay_return_from_checkout(self, **data):
        """Process the notification data sent by SAFERPAY after redirection"""
        _logger.info("Handling return from SaferPay with data: %s", data)
        tx_sudo = None

        try:
            # 1. Try to find the transaction by reference in query param or session
            tx_ref = data.get('tx_ref')
            if not tx_ref and request.session.get('saferpay_data'):
                tx_ref = request.session['saferpay_data'].get('tx_ref')

            if tx_ref:
                tx_sudo = request.env['payment.transaction'].sudo().search([
                    ('reference', '=', tx_ref),
                    ('provider_code', '=', 'saferpay'),
                ], limit=1)

            # 2. Fallback to monitored transaction in session
            if not tx_sudo and request.session.get('__payment_monitored_tx_id__'):
                tx_sudo = request.env['payment.transaction'].sudo().browse(
                    request.session['__payment_monitored_tx_id__']
                ).exists()

            # If transaction is already processed, redirect directly to status
            if tx_sudo and tx_sudo.state in ('done', 'cancel', 'error'):
                request.session['__payment_monitored_tx_id__'] = tx_sudo.id
                return request.redirect('/payment/status')

            # 3. Retrieve the initialization Token
            token = data.get('token')
            if not token and request.session.get('saferpay_data'):
                token = request.session['saferpay_data'].get('token')
            if not token and tx_sudo and tx_sudo.state == 'draft' and tx_sudo.provider_reference:
                token = tx_sudo.provider_reference

            # 4. If transaction and token found, call Saferpay Assert API
            if tx_sudo and token:
                try:
                    provider_details = tx_sudo.provider_id
                    api_url = provider_details._saferpay_get_api_url()
                    credentials = f"{provider_details.username}:{provider_details.password}"
                    base64_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
                    authorization_header = f'Basic {base64_credentials}'
                    url = f"{api_url}/Payment/v1/PaymentPage/Assert"
                    payload = json.dumps({
                        "RequestHeader": {
                            "SpecVersion": "1.33",
                            "CustomerId": str(provider_details.customer),
                            "RequestId": str(tx_sudo.id),
                            "RetryIndicator": 0,
                        },
                        "Token": token,
                    })
                    headers = {
                        'Content-Type': 'application/json; charset=utf-8',
                        'Accept': 'application/json',
                        'SpecVersion': '1.33',
                        'RetryIndicator': '0',
                        'Authorization': authorization_header,
                    }
                    response = requests.post(url, headers=headers, data=payload, timeout=30)
                    transaction_details = response.json()
                    _logger.info("SaferPay Assert response: %s", transaction_details)

                    # Ensure reference and order_id are present so _search_by_reference resolves
                    transaction_details['reference'] = tx_sudo.reference
                    transaction_details['order_id'] = str(tx_sudo.id)

                    # Record transaction details into Odoo payment system
                    tx_sudo._record(transaction_details)

                    # Ensure session monitors this transaction for /payment/status
                    request.session['__payment_monitored_tx_id__'] = tx_sudo.id
                    return request.redirect('/payment/status')
                except Exception as e:
                    _logger.exception("Failed to assert SaferPay payment: %s", e)
                    if tx_sudo:
                        tx_sudo.with_context(payment_safe_write=True)._set_error(
                            f"SaferPay assertion error: {e}"
                        )
                        request.session['__payment_monitored_tx_id__'] = tx_sudo.id
                        return request.redirect('/payment/status')

            # Fallback if transaction is found but token could not be asserted
            if tx_sudo:
                request.session['__payment_monitored_tx_id__'] = tx_sudo.id
                return request.redirect('/payment/status')

        except Exception as e:
            _logger.exception("Unexpected error in SaferPay return handler: %s", e)
            if tx_sudo:
                request.session['__payment_monitored_tx_id__'] = tx_sudo.id
                return request.redirect('/payment/status')

        return request.redirect('/shop/payment')
