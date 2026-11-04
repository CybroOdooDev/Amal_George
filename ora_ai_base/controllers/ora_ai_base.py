# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#############################################################################
import json
import logging
from odoo import http
from odoo.fields import Command
from odoo.http import request

_logger = logging.getLogger(__name__)


class VapiAssistant(http.Controller):

    def _verify_webhook_secret(self):
        """Verifies whether the incoming request matches the configured webhook secret."""
        expected_secret = request.env['ir.config_parameter'].sudo().get_str(
            'ora_ai_base.vapi_webhook_secret')
        if not expected_secret:
            return True
        headers = request.httprequest.headers
        incoming_secret = (
            headers.get('x-vapi-secret') or
            headers.get('X-Vapi-Secret') or
            headers.get('Authorization', '').replace('Bearer ', '').strip() or
            request.httprequest.args.get('token')
        )
        return incoming_secret == expected_secret

    def _parse_request_data(self):
        """Safely parses JSON payload from http request."""
        try:
            return request.httprequest.get_json(silent=True) or request.get_json_data() or {}
        except Exception:
            try:
                raw = request.httprequest.data
                return json.loads(raw) if raw else {}
            except Exception:
                return {}

    @http.route('/vapi_voice_assistant/details', type='jsonrpc',
                auth='public', csrf=False, methods=['POST'])
    def final_details(self):
        """Processes final order details received from the voice assistant
         and creates a Sale Order in Odoo for both telephone and web calls."""
        if not self._verify_webhook_secret():
            _logger.warning("Unauthorized Vapi webhook request: invalid secret")
            return {"error": "Unauthorized"}

        try:
            data = self._parse_request_data()
            message_data = data.get('message', {})
            call = message_data.get('call', {}) or data.get('call', {})
            call_type = call.get('type') or 'webCall'
            vapi_call_id = call.get('id') or data.get('call_id')
            assistant_vapi_id = call.get('assistantId')
            assistant = False
            if assistant_vapi_id:
                assistant = request.env['ora.ai'].sudo().search(
                    [('id_assistant', '=', assistant_vapi_id)], limit=1)

            tool_calls = message_data.get('toolCalls') or message_data.get('tool_calls') or data.get('toolCalls') or []
            tool_call_id = tool_calls[0].get('id') if tool_calls else "tool_call_order"

            pr_list = []
            customer_name = ""
            if tool_calls:
                arguments = tool_calls[0].get('function', {}).get('arguments', {})
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except Exception:
                        arguments = {}
                order_details = arguments.get('OrderDetails', {}) if isinstance(arguments, dict) else {}
                details = order_details.get('Products', []) if isinstance(order_details, dict) else []
                for rec in details:
                    pr_list.append({
                        "customer": rec.get('Customer', ''),
                        "product": rec.get('Product', ''),
                        "id": rec.get('productId'),
                        "qty": rec.get('Quantity', 1),
                        "variant": rec.get('Variant', '-')
                    })
                    if rec.get('Customer'):
                        customer_name = rec.get('Customer')

            # Broadcast live order details to Owl component
            channel = "vapi_voice_channel"
            message = {"value": pr_list, "channel": channel}
            request.env["bus.bus"]._sendone(channel, "notification", message)

            # Check for Test Mode (Skip order and customer creation in test mode)
            assistant_overrides = call.get('assistantOverrides') or {}
            var_values = assistant_overrides.get('variableValues') or call.get('variableValues') or {}
            metadata = call.get('metadata') or data.get('metadata') or {}
            is_test_mode = (
                var_values.get('test_mode') in ('true', True, '1', 1) or
                metadata.get('test_mode') in ('true', True, '1', 1) or
                data.get('test_mode') in ('true', True, '1', 1) or
                request.params.get('test_mode') in ('true', True, '1', 1)
            )

            if is_test_mode:
                _logger.info("Test Mode Call %s: Order details received for configuration test only. No sale order or partner will be created.", vapi_call_id)
                return {
                    "results": [{
                        "toolCallId": tool_call_id,
                        "result": "Configuration verified: Order test acknowledged successfully. No order or customer created in test mode."
                    }]
                }

            # Idempotency check: if an order was already created for this call, do not duplicate
            if vapi_call_id:
                existing_call = request.env['ora.call.history'].sudo().search(
                    [('vapi_call_id', '=', vapi_call_id)], limit=1)
                if existing_call and existing_call.order_id:
                    _logger.info("Order %s already created for call %s",
                                 existing_call.order_id.name, vapi_call_id)
                    return {
                        "results": [{
                            "toolCallId": tool_call_id,
                            "result": f"Order {existing_call.order_id.name} already placed."
                        }]
                    }

            # Filter and validate products
            valid_lines = []
            for item in pr_list:
                pid = item.get('id')
                qty = float(item.get('qty') or 1)
                if not pid or qty <= 0:
                    continue
                product = request.env['product.product'].sudo().browse(pid)
                if product.exists() and product.sale_ok:
                    valid_lines.append(Command.create({
                        'product_id': product.id,
                        'product_uom_qty': qty,
                    }))

            if valid_lines:
                # Customer Identification
                partner = False
                phone_number = call.get('customer', {}).get('number')

                if call_type == 'webCall':
                    if request.env.user and not request.env.user._is_public():
                        partner = request.env.user.partner_id
                    elif customer_name:
                        partner = request.env['res.partner'].sudo().search(
                            [('name', '=ilike', customer_name.strip())], limit=1)
                        if not partner:
                            partner = request.env['res.partner'].sudo().create({
                                'name': customer_name.strip()
                            })
                    else:
                        partner = request.env['res.partner'].sudo().search(
                            [('name', '=', 'Web Voice Customer')], limit=1)
                        if not partner:
                            partner = request.env['res.partner'].sudo().create({
                                'name': 'Web Voice Customer'
                            })
                else:  # inboundPhoneCall or other phone calls
                    if phone_number:
                        partner = request.env['res.partner'].sudo().search(
                            ['|', ('phone', '=', phone_number), ('mobile', '=', phone_number)],
                            limit=1)
                    if not partner and phone_number:
                        partner = request.env['res.partner'].sudo().create({
                            'name': customer_name.strip() if customer_name else f"Voice Customer {phone_number}",
                            'phone': phone_number,
                        })
                    elif not partner and customer_name:
                        partner = request.env['res.partner'].sudo().search(
                            [('name', '=ilike', customer_name.strip())], limit=1)
                        if not partner:
                            partner = request.env['res.partner'].sudo().create({
                                'name': customer_name.strip()
                            })
                    elif not partner:
                        partner = request.env['res.partner'].sudo().search(
                            [('name', '=', 'Voice Customer')], limit=1)
                        if not partner:
                            partner = request.env['res.partner'].sudo().create({
                                'name': 'Voice Customer'
                            })

                order_vals = {
                    'partner_id': partner.id,
                    'order_line': valid_lines,
                }
                if assistant and assistant.company_id:
                    order_vals['company_id'] = assistant.company_id.id
                elif partner.company_id:
                    order_vals['company_id'] = partner.company_id.id

                sales = request.env['sale.order'].sudo().create(order_vals)

                # Check auto-confirm setting
                auto_confirm = request.env['ir.config_parameter'].sudo().get_str(
                    'ora_ai_base.voice_order_auto_confirm') == 'True'
                if auto_confirm:
                    sales.action_confirm()

                # Link order to call history
                if vapi_call_id:
                    call_record = request.env['ora.call.history'].sudo().search(
                        [('vapi_call_id', '=', vapi_call_id)], limit=1)
                    if call_record:
                        call_record.write({
                            'order_id': sales.id,
                            'partner_id': partner.id,
                            'assistant_id': assistant.id if assistant else call_record.assistant_id.id,
                        })
                    else:
                        request.env['ora.call.history'].sudo().create({
                            'vapi_call_id': vapi_call_id,
                            'name': f"Call-{vapi_call_id[:8]}",
                            'order_id': sales.id,
                            'partner_id': partner.id,
                            'call_type': call_type,
                            'assistant_id': assistant.id if assistant else False,
                            'company_id': sales.company_id.id,
                        })

                # Broadcast confirmation notification
                request.env["bus.bus"]._sendone(
                    channel, "notification",
                    {"value": pr_list, "channel": channel, "order_id": sales.id, "order_name": sales.name}
                )

                return {
                    "results": [{
                        "toolCallId": tool_call_id,
                        "result": f"Order {sales.name} successfully created with {len(valid_lines)} items."
                    }]
                }

        except Exception as e:
            _logger.exception("Error processing Vapi final details: %s", e)
            return {"error": str(e)}

        return {"results": [{"toolCallId": "tool_call_order", "result": "No valid products found."}]}

    @http.route('/vapi_voice_assistant/status', type='jsonrpc',
                auth='public', csrf=False, methods=['POST'])
    def get_status(self):
        """Receives status updates from the voice assistant, records call history,
         and broadcasts updates to the bus."""
        if not self._verify_webhook_secret():
            _logger.warning("Unauthorized Vapi status webhook: invalid secret")
            return {"error": "Unauthorized"}

        try:
            data = self._parse_request_data()
            # Log call history and transcript
            request.env['ora.call.history'].sudo().log_call_status(data)

            # Broadcast status to Owl component
            channel = "vapi_voice_channel"
            message = {"value": data, "channel": channel}
            request.env["bus.bus"]._sendone(channel, "notification", message)
            return {"status": "ok"}
        except Exception as e:
            _logger.exception("Error processing Vapi status: %s", e)
            return {"error": str(e)}

    @http.route('/vapi_voice_assistant/language_details', type='jsonrpc',
                auth='public', csrf=False, methods=['POST'])
    def get_language_details(self):
        """Processes user language preferences requested by the voice assistant."""
        if not self._verify_webhook_secret():
            _logger.warning("Unauthorized Vapi language webhook: invalid secret")
            return {"error": "Unauthorized"}

        try:
            data = self._parse_request_data()
            message_data = data.get('message', {})
            tool_calls = message_data.get('toolCalls') or message_data.get('tool_calls') or data.get('toolCalls') or []
            tool_call_id = tool_calls[0].get('id') if tool_calls else "tool_call_lang"

            lang_code = ""
            if tool_calls:
                arguments = tool_calls[0].get('function', {}).get('arguments', {})
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except Exception:
                        arguments = {}
                pref = arguments.get('LanguagePreference', {}) if isinstance(arguments, dict) else {}
                lang_code = pref.get('LanguageCode', '')

            result_msg = f"Language preference received: {lang_code}"
            if lang_code:
                # Find matching language in Odoo
                clean_code = lang_code.replace('-', '_')
                matched_lang = request.env['res.lang'].sudo().search(
                    ['|', ('code', '=', clean_code), ('code', '=ilike', f"{clean_code[:2]}%")],
                    limit=1)
                if matched_lang:
                    result_msg = f"Language successfully set to {matched_lang.name} ({matched_lang.code})"
                    # If caller has an identified partner, update user's language preference
                    call = message_data.get('call', {}) or data.get('call', {})
                    phone_number = call.get('customer', {}).get('number')
                    partner = False
                    if phone_number:
                        partner = request.env['res.partner'].sudo().search(
                            ['|', ('phone', '=', phone_number), ('mobile', '=', phone_number)], limit=1)
                    elif request.env.user and not request.env.user._is_public():
                        partner = request.env.user.partner_id
                    if partner:
                        partner.sudo().write({'lang': matched_lang.code})

            return {
                "results": [{
                    "toolCallId": tool_call_id,
                    "result": result_msg
                }]
            }
        except Exception as e:
            _logger.exception("Error processing Vapi language details: %s", e)
            return {"error": str(e)}
