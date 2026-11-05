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
import re
from odoo import http
from odoo.fields import Command
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class JsonResponse(Response):
    """HTTP JSON response that also acts like a dict for direct unit test access."""
    def __init__(self, data, status=200):
        self._json_data = data
        super().__init__(
            json.dumps(data),
            status=status,
            content_type='application/json;charset=utf-8'
        )

    def __getitem__(self, key):
        return self._json_data[key]

    def get(self, key, default=None):
        return self._json_data.get(key, default)

    def __contains__(self, key):
        return key in self._json_data


class VapiAssistant(http.Controller):

    def _make_json_response(self, data, status=200):
        """Returns pure JSON HTTP response for Vapi webhooks, compatible with both HTTP runtime and unit test mocks."""
        return JsonResponse(data, status=status)

    def _make_tool_response(self, tool_call_id, result_str, status=200):
        """Constructs and returns a Vapi-compliant tool call result payload."""
        payload = {
            "results": [{
                "toolCallId": tool_call_id or "tool_call",
                "result": result_str,
            }]
        }
        return self._make_json_response(payload, status=status)

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
        parsed = {}
        try:
            parsed = request.httprequest.get_json(silent=True) or request.get_json_data() or {}
        except Exception:
            try:
                raw = request.httprequest.data
                parsed = json.loads(raw) if raw else {}
            except Exception:
                parsed = {}
        if isinstance(parsed, dict) and 'params' in parsed and isinstance(parsed['params'], dict) and 'jsonrpc' in parsed:
            return parsed['params']
        return parsed or request.params or {}

    @http.route('/vapi_voice_assistant/details', type='http',
                auth='public', csrf=False, methods=['POST'])
    def final_details(self, **kwargs):
        """Processes final order details received from the voice assistant
         and creates a Sale Order in Odoo for both telephone and web calls."""
        if not self._verify_webhook_secret():
            _logger.warning("Unauthorized Vapi webhook request: invalid secret")
            return self._make_json_response({"error": "Unauthorized"}, status=401)

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
            try:
                request.env["bus.bus"]._sendone(channel, "notification", message)
            except Exception:
                pass

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
                return self._make_tool_response(
                    tool_call_id,
                    "Configuration verified: Order test acknowledged successfully. No order or customer created in test mode."
                )

            # Idempotency check: if an order was already created for this call, do not duplicate
            if vapi_call_id:
                existing_call = request.env['ora.call.history'].sudo().search(
                    [('vapi_call_id', '=', vapi_call_id)], limit=1)
                if existing_call and existing_call.order_id:
                    _logger.info("Order %s already created for call %s",
                                 existing_call.order_id.name, vapi_call_id)
                    return self._make_tool_response(
                        tool_call_id,
                        f"Order {existing_call.order_id.name} already placed."
                    )

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
                company_id = assistant.company_id.id if assistant and assistant.company_id else False

                selected_partner_id = (
                    order_details.get('partnerId') or
                    order_details.get('partner_id') or
                    arguments.get('partnerId') or
                    arguments.get('partner_id') or
                    var_values.get('partner_id') or
                    var_values.get('customer_id') or
                    metadata.get('partner_id') or
                    metadata.get('customer_id') or
                    request.params.get('partner_id')
                )

                # Strict requirement: only support sale order creation after customer selection
                clean_name = re.sub(r'^[^\w]+|[^\w]+$', '', customer_name).strip() if customer_name else ""
                has_customer_info = bool(selected_partner_id or clean_name or phone_number)
                if not has_customer_info:
                    _logger.warning("Order creation rejected for call %s: Customer selection is required first.", vapi_call_id)
                    return self._make_tool_response(
                        tool_call_id,
                        "Sale order creation is only supported after the customer has been identified or selected. "
                        "Please ask whether this order is for an existing or new customer and get their name."
                    )

                # 1. Use explicitly selected customer if provided
                if selected_partner_id:
                    try:
                        p = request.env['res.partner'].sudo().browse(int(selected_partner_id))
                        if p.exists():
                            partner = p
                    except (ValueError, TypeError):
                        partner = False

                # 2. Match spoken customer name against existing customers; only create if not found
                if not partner and clean_name:
                    domain = [('type', '!=', 'private'), ('name', '=ilike', clean_name)]
                    if company_id:
                        domain = [('company_id', 'in', [False, company_id])] + domain
                    partner = request.env['res.partner'].sudo().search(domain, limit=1)

                    if not partner:
                        sub_domain = [('type', '!=', 'private'), '|', ('name', 'ilike', clean_name), ('display_name', 'ilike', clean_name)]
                        if company_id:
                            sub_domain = [('company_id', 'in', [False, company_id])] + sub_domain
                        partner = request.env['res.partner'].sudo().search(sub_domain, limit=1)

                    if not partner:
                        tokens = [t for t in re.split(r'\s+', clean_name) if len(t) > 2]
                        if len(tokens) > 1:
                            tok_domain = [('type', '!=', 'private')]
                            for tok in tokens:
                                tok_domain.append(('name', 'ilike', tok))
                            if company_id:
                                tok_domain = [('company_id', 'in', [False, company_id])] + tok_domain
                            partner = request.env['res.partner'].sudo().search(tok_domain, limit=1)

                    if not partner:
                        partner = request.env['res.partner'].sudo().create({
                            'name': clean_name,
                            'company_id': company_id or False,
                        })

                # 3. Match by phone number for phone calls
                if not partner and phone_number:
                    p_domain = ['|', ('phone', '=', phone_number), ('mobile', '=', phone_number)]
                    if company_id:
                        p_domain = [('company_id', 'in', [False, company_id])] + p_domain
                    partner = request.env['res.partner'].sudo().search(p_domain, limit=1)
                    if not partner:
                        partner = request.env['res.partner'].sudo().create({
                            'name': f"Voice Customer {phone_number}",
                            'phone': phone_number,
                            'company_id': company_id or False,
                        })

                # 4. Fallback when neither selected nor spoken
                if not partner:
                    if call_type == 'webCall' and request.env.user and not request.env.user._is_public():
                        partner = request.env.user.partner_id
                    else:
                        fallback_name = 'Web Voice Customer' if call_type == 'webCall' else 'Voice Customer'
                        partner = request.env['res.partner'].sudo().search([('name', '=', fallback_name)], limit=1)
                        if not partner:
                            partner = request.env['res.partner'].sudo().create({
                                'name': fallback_name,
                                'company_id': company_id or False,
                            })

                # Salesperson resolution (logged-in user)
                salesperson_id = (
                    order_details.get('salesperson_id') or
                    order_details.get('salespersonId') or
                    order_details.get('user_id') or
                    order_details.get('userId') or
                    arguments.get('salesperson_id') or
                    arguments.get('salespersonId') or
                    arguments.get('user_id') or
                    arguments.get('userId') or
                    var_values.get('salesperson_id') or
                    var_values.get('user_id') or
                    metadata.get('salesperson_id') or
                    metadata.get('user_id') or
                    request.params.get('salesperson_id') or
                    request.params.get('user_id')
                )

                salesperson = False
                if salesperson_id:
                    try:
                        u = request.env['res.users'].sudo().browse(int(salesperson_id))
                        if u.exists():
                            salesperson = u
                    except (ValueError, TypeError):
                        salesperson = False

                # Fallback 1: Dedicated salesperson assigned to the customer in Odoo contacts
                if not salesperson and partner and partner.user_id:
                    salesperson = partner.user_id

                # Fallback 2: Authenticated user (if not public or root)
                if not salesperson and request.env.user and not request.env.user._is_public() and request.env.user.id != 1:
                    salesperson = request.env.user

                # Fallback 3: Assistant creator / configured user
                if not salesperson and assistant and assistant.create_uid:
                    salesperson = assistant.create_uid

                # Fallback 4: Active sales administrator (Mitchell Admin ID 2)
                if not salesperson:
                    admin_u = request.env['res.users'].sudo().browse(2)
                    if admin_u.exists():
                        salesperson = admin_u

                order_vals = {
                    'partner_id': partner.id,
                    'order_line': valid_lines,
                }
                if salesperson:
                    order_vals['user_id'] = salesperson.id
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
                        history_vals = {
                            'order_id': sales.id,
                            'partner_id': partner.id,
                            'assistant_id': assistant.id if assistant else call_record.assistant_id.id,
                        }
                        if salesperson:
                            history_vals['user_id'] = salesperson.id
                        call_record.write(history_vals)
                    else:
                        history_vals = {
                            'vapi_call_id': vapi_call_id,
                            'name': f"Call-{vapi_call_id[:8]}",
                            'order_id': sales.id,
                            'partner_id': partner.id,
                            'call_type': call_type,
                            'assistant_id': assistant.id if assistant else False,
                            'company_id': sales.company_id.id,
                        }
                        if salesperson:
                            history_vals['user_id'] = salesperson.id
                        request.env['ora.call.history'].sudo().create(history_vals)

                # Broadcast confirmation notification
                request.env["bus.bus"]._sendone(
                    channel, "notification",
                    {"value": pr_list, "channel": channel, "order_id": sales.id, "order_name": sales.name}
                )

                return self._make_tool_response(
                    tool_call_id,
                    f"Order {sales.name} successfully created with {len(valid_lines)} items for customer {partner.name}."
                )

        except Exception as e:
            _logger.exception("Error processing Vapi final details: %s", e)
            return self._make_tool_response(
                tool_call_id if 'tool_call_id' in locals() else "tool_call_order",
                f"Internal error creating order: {str(e)}",
                status=500
            )

        return self._make_tool_response("tool_call_order", "No valid products found to order.")

    @http.route('/vapi_voice_assistant/status', type='http',
                auth='public', csrf=False, methods=['POST'])
    def get_status(self, **kwargs):
        """Receives status updates from the voice assistant, records call history,
         and broadcasts updates to the bus."""
        if not self._verify_webhook_secret():
            _logger.warning("Unauthorized Vapi status webhook: invalid secret")
            return self._make_json_response({"error": "Unauthorized"}, status=401)

        try:
            data = self._parse_request_data()
            # Log call history and transcript
            request.env['ora.call.history'].sudo().log_call_status(data)

            # Broadcast status to Owl component
            channel = "vapi_voice_channel"
            message = {"value": data, "channel": channel}
            request.env["bus.bus"]._sendone(channel, "notification", message)
            return self._make_json_response({"status": "ok"})
        except Exception as e:
            _logger.exception("Error processing Vapi status: %s", e)
            return self._make_json_response({"error": str(e)}, status=500)

    @http.route('/vapi_voice_assistant/language_details', type='http',
                auth='public', csrf=False, methods=['POST'])
    def get_language_details(self, **kwargs):
        """Processes user language preferences requested by the voice assistant."""
        if not self._verify_webhook_secret():
            _logger.warning("Unauthorized Vapi language webhook: invalid secret")
            return self._make_json_response({"error": "Unauthorized"}, status=401)

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

            return self._make_tool_response(tool_call_id, result_msg)
        except Exception as e:
            _logger.exception("Error processing Vapi language details: %s", e)
            return self._make_tool_response(
                tool_call_id if 'tool_call_id' in locals() else "tool_call_lang",
                f"Error processing language details: {str(e)}",
                status=500
            )

    @http.route('/vapi_voice_assistant/check_customer', type='http',
                auth='public', csrf=False, methods=['POST'])
    def check_customer(self, **kwargs):
        """Checks if a customer name exists in Odoo res.partner for voice assistant."""
        if not self._verify_webhook_secret():
            _logger.warning("Unauthorized Vapi customer check webhook: invalid secret")
            return self._make_json_response({"error": "Unauthorized"}, status=401)

        try:
            data = self._parse_request_data()
            message_data = data.get('message', {})
            tool_calls = message_data.get('toolCalls') or message_data.get('tool_calls') or data.get('toolCalls') or []
            tool_call_id = tool_calls[0].get('id') if tool_calls else "tool_call_check_customer"

            arguments = {}
            if tool_calls:
                raw_args = tool_calls[0].get('function', {}).get('arguments', {})
                if isinstance(raw_args, str):
                    try:
                        arguments = json.loads(raw_args)
                    except Exception:
                        arguments = {}
                elif isinstance(raw_args, dict):
                    arguments = raw_args

            raw_name = (
                arguments.get('customer_name') or
                arguments.get('customer') or
                arguments.get('name') or
                data.get('customer_name') or ""
            )
            # Robust punctuation and whitespace stripping
            clean_name = re.sub(r'^[^\w]+|[^\w]+$', '', raw_name).strip() if raw_name else ""

            if not clean_name:
                return self._make_tool_response(
                    tool_call_id,
                    "No customer name was provided to check. Please ask the user for the customer's name."
                )

            Partner = request.env['res.partner'].sudo()
            partner = Partner.search([
                ('type', '!=', 'private'),
                ('name', '=ilike', clean_name)
            ], limit=1)

            if not partner:
                partner = Partner.search([
                    ('type', '!=', 'private'),
                    '|', ('name', 'ilike', clean_name),
                    ('display_name', 'ilike', clean_name)
                ], limit=1)

            if not partner:
                tokens = [t for t in re.split(r'\s+', clean_name) if len(t) > 2]
                if len(tokens) > 1:
                    tok_domain = [('type', '!=', 'private')]
                    for tok in tokens:
                        tok_domain.append(('name', 'ilike', tok))
                    partner = Partner.search(tok_domain, limit=1)

            if partner:
                # Live sync with Owl frontend dropdown
                try:
                    request.env["bus.bus"]._sendone(
                        "vapi_voice_channel", "notification",
                        {
                            "type": "customer_selected",
                            "partner_id": partner.id,
                            "partner_name": partner.display_name or partner.name,
                        }
                    )
                except Exception:
                    pass

                return self._make_tool_response(
                    tool_call_id,
                    f"Customer '{partner.name}' was FOUND in the existing customer database (ID: {partner.id}). "
                    f"Inform the caller that {partner.name} is verified and ask what products they want to order."
                )
            else:
                return self._make_tool_response(
                    tool_call_id,
                    f"Customer '{clean_name}' was NOT FOUND in the existing customer database. "
                    f"Inform the caller that no existing account was found for '{clean_name}', and ask: "
                    f"'Would you like me to create a new customer account for {clean_name}, or check with another name?'"
                )

        except Exception as e:
            _logger.exception("Error checking customer in Vapi webhook: %s", e)
            return self._make_tool_response(
                tool_call_id if 'tool_call_id' in locals() else "tool_call_check_customer",
                f"Could not verify customer due to an internal error: {str(e)}",
                status=500
            )
