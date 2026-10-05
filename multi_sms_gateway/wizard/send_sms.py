# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import logging
import re

import vonage
from vonage_sms import SmsMessage
from telesign.messaging import MessagingClient
from twilio.rest import Client

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SendSms(models.TransientModel):
    """
    Class for the wizard to send SMS.
    Methods:
        action_send_sms():
            Button action to send SMS.
        _normalize_phone_number(number, country):
            Normalizes phone numbers to standard E.164.
    """
    _name = 'send.sms'
    _description = 'Wizard to send SMS'

    sms_id = fields.Many2one('sms.gateway.config', string='Connection ID',
                             help='Gateway record with credentials')
    sms_to = fields.Char(string='Send To',
                         help='Enter the number to send the SMS')
    text = fields.Text(string='Text', required=True,
                       help='Enter the text for the SMS')

    def _normalize_phone_number(self, number, country=None):
        """
        Normalize a recipient phone number to E.164 format (+[country_code][number]).
        Handles:
        - Numbers with spaces, hyphens, brackets, dots
        - Numbers already starting with '+'
        - National trunk prefixes (leading '0', e.g. 08089988064 -> +918089988064)
        - Local format without country code using partner or company country
        - International numbers without leading '+' (e.g. 918089988064 -> +918089988064)
        """
        if not number or not isinstance(number, str):
            return False
        number = number.strip()
        if not number:
            return False

        country_code = country.code if country and hasattr(country, 'code') and country.code else None
        country_phone_code = country.phone_code if country and hasattr(country, 'phone_code') and country.phone_code else None

        formatted = None
        try:
            from odoo.addons.phone_validation.tools import phone_validation
            # If number already starts with '+', omit region to preserve international prefix
            region = None if number.startswith('+') else country_code
            formatted = phone_validation.phone_format(
                number,
                region,
                country_phone_code,
                force_format='E164',
                raise_exception=False,
            )
        except Exception as e:
            _logger.debug("phone_validation error for %s: %s", number, e)
            formatted = None

        if formatted and formatted.startswith('+') and formatted != number:
            clean_e164 = '+' + re.sub(r'\D', '', formatted[1:])
            if len(clean_e164) > 1:
                return clean_e164
        elif formatted and formatted.startswith('+') and re.match(r'^\+\d{7,15}$', formatted):
            return formatted

        # Fallback normalization if phone_validation could not parse or returned original
        clean_digits = re.sub(r'\D', '', number)
        if not clean_digits:
            return False

        if number.startswith('+'):
            return f"+{clean_digits}"

        if country_phone_code:
            cc_str = str(country_phone_code)
            # Remove leading national trunk zero (e.g. 08089988064 -> 8089988064)
            if clean_digits.startswith('0') and not clean_digits.startswith('00'):
                trunk_stripped = clean_digits.lstrip('0')
                if trunk_stripped:
                    clean_digits = trunk_stripped

            if clean_digits.startswith(cc_str) and len(clean_digits) > len(cc_str) + 6:
                return f"+{clean_digits}"
            return f"+{cc_str}{clean_digits}"

        return f"+{clean_digits}"

    def action_send_sms(self):
        """
        Function to send SMS using different SMS gateways (Vonage, Twilio, TeleSign).
        """
        self.ensure_one()
        if not self.sms_id:
            raise UserError(_('Please select an SMS Gateway configuration.'))
        if not self.sms_to:
            raise UserError(_('Please provide a recipient phone number.'))

        raw_numbers = [num.strip() for num in self.sms_to.split(',') if num.strip()]
        if not raw_numbers:
            raise UserError(_('Please provide at least one valid phone number.'))

        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        country = None
        if active_model == 'res.partner' and active_id and active_model in self.env:
            partner_rec = self.env[active_model].browse(active_id)
            country = getattr(partner_rec, 'country_id', None)
        if not country:
            country = self.env.company.country_id

        normalized_numbers = []
        for raw_num in raw_numbers:
            norm = self._normalize_phone_number(raw_num, country=country)
            if norm:
                normalized_numbers.append(norm)
            else:
                _logger.warning("Could not normalize recipient phone number: %s", raw_num)
                clean = re.sub(r'[^\d+]', '', raw_num)
                if clean:
                    normalized_numbers.append(clean)

        if not normalized_numbers:
            raise UserError(_('No valid phone numbers found to send SMS.'))

        gateway = self.sms_id.gateway_name

        if gateway == 'vonage':
            try:
                client = vonage.Vonage(vonage.Auth(
                    api_key=self.sms_id.vonage_key,
                    api_secret=self.sms_id.vonage_secret
                ))
            except Exception as e:
                _logger.error("Failed to initialize Vonage client: %s", e)
                raise UserError(_("Vonage configuration error: %s") % e)

            for number in normalized_numbers:
                try:
                    vonage_num = number.lstrip('+')
                    response = client.sms.send(SmsMessage(
                        to=vonage_num,
                        from_='Vonage APIs',
                        text=self.text
                    ))
                    if response.messages[0].status == "0":
                        _logger.info("Vonage message sent successfully to %s", number)
                    else:
                        err_text = response.messages[0].error_text
                        _logger.warning("Vonage failed for %s: %s", number, err_text)
                        raise UserError(_("Vonage failed to send SMS to %s: %s") % (number, err_text))
                except UserError:
                    raise
                except Exception as e:
                    _logger.error("Vonage error for %s: %s", number, e)
                    raise UserError(_("Vonage error for %s: %s") % (number, e))

        elif gateway == 'twilio':
            try:
                client = Client(self.sms_id.twilio_account_sid,
                                self.sms_id.twilio_auth_token)
            except Exception as e:
                _logger.error("Failed to initialize Twilio client: %s", e)
                raise UserError(_("Twilio configuration error: %s") % e)

            from_num = str(self.sms_id.twilio_phone_number).strip()
            for number in normalized_numbers:
                try:
                    client.messages.create(
                        body=self.text,
                        from_=from_num,
                        to=number
                    )
                    _logger.info("Twilio message sent successfully to %s", number)
                except UserError:
                    raise
                except Exception as e:
                    _logger.error("Twilio error for %s: %s", number, e)
                    raw_msg = getattr(e, 'msg', None) or str(e)
                    clean_msg = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', raw_msg).strip()
                    lower_msg = clean_msg.lower()

                    if 'predefined sms templates' in lower_msg or 'invalid template name' in lower_msg or getattr(e, 'code', None) == 572006:
                        raise UserError(_(
                            "Twilio Trial Account Restriction for %s:\n\n"
                            "Unable to send SMS: Trial accounts can only use predefined SMS templates.\n\n"
                            "Why this happens:\n"
                            "Twilio trial accounts do not allow sending custom message text ('%s'). "
                            "Twilio requires using pre-approved templates on trial accounts to prevent spam.\n\n"
                            "How to fix:\n"
                            "Upgrade your Twilio account from Trial to Paid in the Twilio Console (https://console.twilio.com). "
                            "Once upgraded, you can send any custom SMS message directly from Odoo."
                        ) % (number, self.text))

                    if "verified recipient" in lower_msg or "unverified" in lower_msg or getattr(e, 'code', None) == 21608:
                        raise UserError(_(
                            "Twilio Trial Account Restriction for %s:\n\n"
                            "This destination phone number is not verified in your Twilio trial account.\n\n"
                            "Why this happens:\n"
                            "Twilio trial accounts can only send SMS to phone numbers that have been verified in your Twilio Console.\n\n"
                            "How to fix:\n"
                            "1. Log in to your Twilio Console (https://console.twilio.com)\n"
                            "2. Navigate to: Phone Numbers -> Manage -> Verified Caller IDs\n"
                            "3. Add and verify the destination number '%s'\n"
                            "4. Ensure India (+91) is enabled under Messaging -> Settings -> Geo Permissions\n"
                            "Alternatively, upgrade your Twilio account from Trial to Paid to send messages to any recipient without pre-verification."
                        ) % (number, number))

                    raise UserError(_("Twilio error for %s: %s") % (number, clean_msg))

        elif gateway == 'telesign':
            try:
                messaging = MessagingClient(
                    self.sms_id.telesign_customer,
                    self.sms_id.telesign_api_key)
            except Exception as e:
                _logger.error("Failed to initialize TeleSign client: %s", e)
                raise UserError(_("TeleSign configuration error: %s") % e)

            for number in normalized_numbers:
                try:
                    response = messaging.message(number, self.text, 'ARN')
                except Exception as e:
                    _logger.error("TeleSign connection/request error for %s: %s", number, e)
                    raise UserError(_("TeleSign connection error: %s") % e)

                status_info = response.json.get('status', {}) if isinstance(getattr(response, 'json', None), dict) else {}
                status_code = status_info.get('code')
                status_desc = status_info.get('description', '')

                _logger.info(
                    "TeleSign response for %s: HTTP %s, code %s, description: %s",
                    number, response.status_code, status_code, status_desc
                )

                # Status codes 200 (Delivered/Final OK) and 290 (Message in progress) are successful
                if status_code in (200, 290) or (response.ok and not status_code):
                    _logger.info(
                        "TeleSign SMS successfully dispatched to %s (reference_id: %s)",
                        number,
                        response.json.get('reference_id') if isinstance(getattr(response, 'json', None), dict) else None
                    )
                    continue

                # Handle TeleSign error responses
                _logger.warning(
                    "TeleSign rejected SMS for %s: HTTP %s, status_info: %s",
                    number, response.status_code, status_info
                )

                # Error 11000: Invalid phone number format
                if status_code == 11000 or 'phone_number' in status_desc.lower():
                    raise UserError(_(
                        "TeleSign Error for %s: The phone number format is invalid. "
                        "Please use standard E.164 format with the international country code, e.g. 918089988064."
                    ) % number)

                # Error 10033: Unverified/unauthorized recipient on trial account
                if status_code == 10033 or 'not been verified' in status_desc.lower():
                    raise UserError(_(
                        "TeleSign Error for %s: This phone number has not been verified/authorized for the current TeleSign trial account.\n\n"
                        "This is a TeleSign account restriction, not an Odoo connection error. "
                        "TeleSign trial accounts only permit sending SMS to verified/authorized numbers. "
                        "To send messages to this recipient, the number must be authorized in your TeleSign account or the TeleSign account must be upgraded."
                    ) % number)

                err_msg = status_desc or f"HTTP {response.status_code}"
                raise UserError(_("TeleSign Error for %s: %s (Status Code: %s)") % (number, err_msg, status_code or response.status_code))

        else:
            raise UserError(_("Unsupported SMS Gateway: %s") % (gateway or 'None'))

        self.env['sms.history'].sudo().create({
            'sms_gateway_id': self.sms_id.sms_gateway_id.id,
            'sms_mobile': ', '.join(normalized_numbers),
            'sms_text': self.text,
            'company_id': self.env.company.id,
        })

        if active_model and active_id and active_model in self.env:
            record = self.env[active_model].browse(active_id)
            if hasattr(record, 'message_post'):
                record.message_post(
                    body=f"Message: {self.text}",
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment"
                )
