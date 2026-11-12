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

from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _sanitize_message(self, message):
        if message:
            return str(message)
        return message

    def _set_error(self, message, extra_allowed_states=()):
        message = self._sanitize_message(message)
        return super()._set_error(message, extra_allowed_states=extra_allowed_states)

    def _set_canceled(self, state_message=None):
        state_message = self._sanitize_message(state_message)
        return super()._set_canceled(state_message=state_message)

    def _get_specific_rendering_values(self, processing_values):
        """Rendering the details from processing values,
        the values in the order details, amount and all
        passing as a dict file."""
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'saferpay':
            return res
        # Get provider details
        provider_details = self.provider_id
        if not (provider_details.username and provider_details.password):
            raise ValidationError(self.env._("SaferPay credentials are missing."))
        credentials = f"{provider_details.username}:{provider_details.password}"
        base64_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        authorization_header = f'Basic {base64_credentials}'
        base_url = self.provider_id.get_base_url().rstrip('/')
        amount = payment_utils.to_minor_currency_units(
            processing_values.get('amount'), self.currency_id
        )
        currency_name = self.env['res.currency'].browse(processing_values.get('currency_id')).name
        return_url = f"{base_url}/saferpay/payment/status?tx_ref={self.reference}"
        payload = json.dumps({
            "RequestHeader": {
                "SpecVersion": "1.33",
                "CustomerId": str(provider_details.customer),
                "RequestId": str(self.id),
                "RetryIndicator": 0
            },
            "TerminalId": str(provider_details.terminal),
            "Payment": {
                "Amount": {
                    "Value": str(amount),
                    "CurrencyCode": currency_name
                },
                "OrderId": str(self.id),
                "Description": str(self.reference),
            },
            "ReturnUrl": {  
                "Url": return_url,
            }
        })
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/json',
            'SpecVersion': '1.33',
            'RetryIndicator': '0',
            'Authorization': authorization_header
        }
        api_url = provider_details._saferpay_get_api_url()
        url = f"{api_url}/Payment/v1/PaymentPage/Initialize"
        response = requests.post(url, headers=headers, data=payload, timeout=30)
        response_data = response.json()
        if response.status_code != 200:
            raise ValidationError(self.env._("SaferPay: %s", response_data.get('ErrorMessage', '')))
        token = response_data.get('Token')
        self.with_context(payment_safe_write=True).provider_reference = token
        if request and hasattr(request, 'session'):
            request.session['saferpay_data'] = {
                'token': token,
                'tx_ref': self.reference,
            }
            request.session['__payment_monitored_tx_id__'] = self.id
        return {
            'api_url': response_data['RedirectUrl'],
            'url': response_data['RedirectUrl'],
        }

    @api.model
    def _search_by_reference(self, provider_code, payment_data):
        """Get transaction data based on notification data.
            Args:
                provider_code (str): The provider code for the transaction.
        """
        if provider_code != 'saferpay':
            return super()._search_by_reference(provider_code, payment_data)

        order_id = (
            payment_data.get('OrderId')
            or payment_data.get('Transaction', {}).get('OrderId')
            or payment_data.get('order_id')
        )
        tx = False
        if order_id and str(order_id).isdigit():
            tx = self.search([('id', '=', int(order_id)), ('provider_code', '=', 'saferpay')], limit=1)
        if not tx and payment_data.get('reference'):
            tx = self.search([('reference', '=', payment_data['reference']), ('provider_code', '=', 'saferpay')], limit=1)
        if not tx and payment_data.get('Token'):
            tx = self.search([('provider_reference', '=', payment_data['Token']), ('provider_code', '=', 'saferpay')], limit=1)
        if not tx:
            raise ValidationError(
                self.env._(
                    "SAFERPAY: No transaction found matching reference %s.",
                    order_id or payment_data.get('reference'),
                )
            )
        return tx

    def _extract_amount_data(self, payment_data):
        if self.provider_code != 'saferpay':
            return super()._extract_amount_data(payment_data)

        transaction = payment_data.get('Transaction', {})
        amount_data = transaction.get('Amount')
        
        if not amount_data:
            return None

        return {
            'amount': payment_utils.to_major_currency_units(
                float(amount_data.get('Value')), 
                self.currency_id
            ),
            'currency_code': amount_data.get('CurrencyCode')
        }

    def _apply_updates(self, payment_data):
        """Process the notification data received from the payment provider.
        And checking the status and making the order done based on the status"""
        if self.provider_code != 'saferpay':
            return super()._apply_updates(payment_data)
        
        try:
            transaction = payment_data.get('Transaction', {})
            status = transaction.get('Status')
            if transaction_id := transaction.get('Id'):
                self.with_context(payment_safe_write=True).provider_reference = transaction_id
            _logger.info("SaferPay status received: %s", status)
            
            if status in ('AUTHORIZED', 'CAPTURED'):
                self._set_done()
            elif status == 'PENDING':
                self._set_pending()
            elif status == 'CANCELED':
                self._set_canceled(state_message="Payment canceled")
            elif status == 'FAILED':
                self._set_error("Payment failed")
            elif payment_data.get('ErrorName'):
                error_msg = payment_data.get('ErrorMessage') or payment_data.get('ErrorName')
                self._set_error(f"SaferPay: {error_msg}")
            else:
                _logger.error("Unhandled SaferPay status: %s", status)
                self._set_error(f"saferpay: Invalid payment status ({status}).")
        except Exception as e:
            _logger.error("Error processing SaferPay payment: %s", e)
            self._set_canceled(state_message="Payment canceled")
