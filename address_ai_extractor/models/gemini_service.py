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
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#############################################################################
import json
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

try:
    from google import genai
    from google.genai import errors, types
    from pydantic import BaseModel, Field

    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

    class BaseModel:
        pass

    def Field(*args, **kwargs):
        return None


if HAS_GENAI:
    class AddressExtractionSchema(BaseModel):
        name: Optional[str] = Field(
            default=None,
            description="Recipient person or organization/company name, if present in the address text",
        )
        street: Optional[str] = Field(
            default=None,
            description="Primary street address line, building name, flat/house number, and road",
        )
        street2: Optional[str] = Field(
            default=None,
            description="Secondary address line, suite/apartment number, sub-locality, landmark, or floor",
        )
        city: Optional[str] = Field(
            default=None,
            description="City, town, municipality, or village name",
        )
        state: Optional[str] = Field(
            default=None,
            description="State, province, region, or union territory name or code",
        )
        zip: Optional[str] = Field(
            default=None,
            description="Postal code, ZIP code, or PIN code",
        )
        country: Optional[str] = Field(
            default=None,
            description="Country name or ISO country code",
        )


class GeminiService(models.AbstractModel):
    _name = 'gemini.service'
    _description = 'Google Gemini AI Service'

    DEFAULT_MODEL = 'gemini-3.5-flash'
    CONFIG_API_KEY = 'address_ai_extractor.gemini_api_key'
    CONFIG_MODEL = 'address_ai_extractor.gemini_model'

    def _get_param_value(self, key, default=''):
        """Safely fetch config parameter using Odoo 20 get_str or legacy fallback."""
        params = self.env['ir.config_parameter'].sudo()
        if hasattr(params, 'get_str'):
            return params.get_str(key, default=default)
        if hasattr(params, 'get_param'):
            return params.get_param(key, default=default)
        rec = params.search([('key', '=', key)], limit=1)
        return rec.value if rec and rec.value else default

    def _get_api_key(self):
        """Retrieve the configured Gemini API key from system parameters."""
        api_key = self._get_param_value(self.CONFIG_API_KEY)
        if not api_key or not api_key.strip():
            raise UserError(
                _("Google Gemini API Key is not configured.\n\n"
                  "Please navigate to Settings > AI Address Extractor "
                  "and enter your Gemini API key.")
            )
        return api_key.strip()

    def _get_model_name(self):
        """Retrieve the configured Gemini model name from system parameters."""
        model_name = self._get_param_value(self.CONFIG_MODEL, default=self.DEFAULT_MODEL)
        return model_name.strip() if model_name and model_name.strip() else self.DEFAULT_MODEL

    def _get_client(self, api_key=None):
        """Instantiate and return the Google GenAI SDK Client."""
        if not HAS_GENAI:
            raise UserError(
                _("The official 'google-genai' Python SDK is not installed in this environment.\n"
                  "Please install it using: pip install google-genai")
            )
        key = api_key.strip() if api_key else self._get_api_key()
        return genai.Client(api_key=key)

    def test_connection(self, api_key=None, model_name=None):
        """
        Verify connection to Google Gemini API using the given or configured API key.
        Returns a tuple (success: bool, message: str).
        """
        try:
            client = self._get_client(api_key=api_key)
            model = model_name or self._get_model_name()
            config = types.GenerateContentConfig(
                max_output_tokens=5,
                temperature=0.0,
            )
            response = client.models.generate_content(
                model=model,
                contents="Ping",
                config=config,
            )
            if response and (response.text or response.candidates):
                return True, _("Connection successful! Connected to Google Gemini model '%s'.") % model
            return True, _("Connection successful! Google Gemini responded.")
        except UserError:
            raise
        except Exception as exc:
            error_msg = self._handle_gemini_exception(exc)
            return False, error_msg

    def extract_address(self, address_text):
        """
        Send unstructured address text to Google Gemini and return structured address dict.
        """
        if not address_text or not address_text.strip():
            raise UserError(_("Please provide an address text to extract."))

        cleaned_input = address_text.strip()
        client = self._get_client()
        model = self._get_model_name()

        system_instruction = (
            "You are an expert address parser. Extract structured address components "
            "from the provided address string.\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. Do NOT hallucinate, guess, or invent any missing information.\n"
            "2. If any field (name, street, street2, city, state, zip, country) is not "
            "explicitly stated or directly evident in the address, return it as null.\n"
            "3. Separate street into 'street' (primary number, building, road) and "
            "'street2' (flat/suite, floor, landmark, locality/sub-locality) when possible.\n"
            "4. Return only the structured schema."
        )

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=AddressExtractionSchema,
            temperature=0.0,
        )

        try:
            response = client.models.generate_content(
                model=model,
                contents=cleaned_input,
                config=config,
            )
            return self._parse_extraction_response(response)
        except UserError:
            raise
        except Exception as exc:
            error_msg = self._handle_gemini_exception(exc)
            raise UserError(error_msg)

    def _parse_extraction_response(self, response):
        """Parse and sanitize response from Gemini into a standard dictionary."""
        data = {}
        if hasattr(response, 'parsed') and response.parsed:
            if hasattr(response.parsed, 'model_dump'):
                data = response.parsed.model_dump()
            elif hasattr(response.parsed, '__dict__'):
                data = response.parsed.__dict__
            elif isinstance(response.parsed, dict):
                data = response.parsed

        if not data and response.text:
            try:
                data = json.loads(response.text)
            except Exception:
                data = {}

        fields = ['name', 'street', 'street2', 'city', 'state', 'zip', 'country']
        result = {}
        for field in fields:
            val = data.get(field)
            if val and isinstance(val, str) and val.strip():
                clean_val = val.strip()
                result[field] = clean_val if clean_val.lower() not in ('null', 'none', 'n/a') else False
            else:
                result[field] = False

        return result

    def _handle_gemini_exception(self, exc):
        """Format Gemini exceptions into safe, user-friendly error messages."""
        if HAS_GENAI and isinstance(exc, errors.APIError):
            code = getattr(exc, 'code', None)
            message = getattr(exc, 'message', str(exc))

            if code in (400, 403) or 'API_KEY_INVALID' in str(message) or 'PERMISSION_DENIED' in str(message):
                return _(
                    "Invalid Google Gemini API key or unauthorized request.\n"
                    "Please verify that your API key is correct and has Gemini API access enabled in Google AI Studio."
                )
            if code == 429 or 'RESOURCE_EXHAUSTED' in str(message):
                return _(
                    "Google Gemini API quota exceeded or rate limit reached.\n"
                    "Please wait a moment before trying again, or check your Gemini API plan."
                )
            if code and code >= 500:
                return _(
                    "Google Gemini service is temporarily unavailable (Error %s).\n"
                    "Please try again in a few minutes."
                ) % code

            return _("Google Gemini API error: %s") % (message or str(exc))

        exc_str = str(exc).lower()
        if 'timeout' in exc_str:
            return _("The request to Google Gemini timed out. Please check your internet connectivity and try again.")
        if 'connection' in exc_str or 'network' in exc_str:
            return _("Unable to connect to Google Gemini service. Please verify your server's network connection.")

        return _("An unexpected error occurred while communicating with Google Gemini: %s") % str(exc)
