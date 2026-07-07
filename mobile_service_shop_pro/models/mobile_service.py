# -*- coding: utf-8 -*-
################################################################################
#
#    Mobile Service Management Pro — Odoo 19
#
#    IMEI lookup migrated from imeidb.xyz  →  ImeiCheck.com free API
#    API endpoint: https://alpha.imeicheck.com/api/modelBrandName
#
################################################################################
import json
import logging
import pytz
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MobileService(models.Model):
    """Inherits mobile.service to extend with Pro features:
    - IMEI device lookup via ImeiCheck.com API
    - Real device photo attachment
    - Complaint visibility toggle
    """
    _inherit = 'mobile.service'

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------
    real_phone_image = fields.Binary(
        string="Real Phone Image", attachment=True, store=True,
        help="Attach a photo of the physical device being serviced.")
    complaint_visibility_status = fields.Boolean(
        compute='_compute_complaint_visibility_status',
        help="Mirrors the 'Show complaints' setting from Configuration.")
    active_api = fields.Boolean(
        string="IMEI API Active", compute="_compute_active_api",
        help="Mirrors the 'IMEI device details' toggle from Configuration.")
    manufacturer = fields.Char(
        string="Manufacturer", help="Manufacturer populated automatically from IMEI lookup.")
    device_name = fields.Char(
        string="Device Name", help="Full device name populated automatically from IMEI lookup.")

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('person_name')
    def _compute_active_api(self):
        """Mirror the IMEI API enabled flag from system parameters."""
        for rec in self:
            rec.active_api = rec._get_bool_config('get_api_details')

    @api.model
    def _is_truthy_param(self, value):
        """Normalize string config parameters to booleans."""
        return str(value).strip().lower() in ('true', '1', 'yes', 'on')

    @api.model
    def _get_config_param(self, key, default=False):
        """Read the renamed module parameter, falling back to the old suffix name."""
        config = self.env['ir.config_parameter'].sudo()
        new_key = f'mobile_service_shop_pro.{key}'
        old_key = f'mobile_service_shop_pro_19.{key}'
        value = config.get_param(new_key)
        if value in (None, ''):
            value = config.get_param(old_key, default)
        return value

    @api.model
    def _get_bool_config(self, key):
        """Read a boolean config parameter for this addon."""
        return self._is_truthy_param(self._get_config_param(key))

    @api.depends('service_state')
    def _compute_complaint_visibility_status(self):
        """Mirror the show-complaints setting from system parameters."""
        for rec in self:
            rec.complaint_visibility_status = rec._get_bool_config('show_complain_types')

    # ------------------------------------------------------------------
    # Service ticket report
    # ------------------------------------------------------------------
    def get_ticket(self):
        """Generate the printable service ticket PDF with timezone-aware timestamp."""
        self.ensure_one()
        user = self.env['res.users'].browse(self.env.uid)
        if user.tz:
            tz = pytz.timezone(user.tz)
            time = pytz.utc.localize(datetime.now()).astimezone(tz)
            date_today = time.strftime("%Y-%m-%d %H:%M %p")
        else:
            date_today = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

        complaint_text = ""
        description_text = ""
        complaint_ids = self.env['mobile.complaint.tree'].search(
            [('complaint_id', '=', self.id)]
        )
        for complaint in complaint_ids:
            comp_type = complaint.complaint_type_tree
            description = complaint.description_tree
            complaint_text = comp_type.complaint_type + ", " + complaint_text
            if description.description:
                description_text = description.description + ", " + description_text

        data = {
            'ids': self.ids,
            'model': self._name,
            'date_today': date_today,
            'date_request': self.date_request,
            'date_return': self.return_date,
            'sev_id': self.name,
            'real_phone_image': self.real_phone_image,
            'warranty': self.is_in_warranty,
            'customer_name': self.person_name.name,
            'imei_no': self.imei_no,
            'technician': self.technician_name.name,
            'complaint_types': complaint_text,
            'complaint_description': description_text,
            'mobile_brand': self.brand_name.brand_name,
            'model_name': self.model_name.mobile_brand_models,
        }
        return self.env.ref(
            'mobile_service_shop.mobile_service_ticket'
        ).report_action(self, data=data)

    # ------------------------------------------------------------------
    # IMEI lookup — ImeiCheck.com API
    # ------------------------------------------------------------------
    def get_device_details(self):
        """Fetch device brand and model from IMEI using ImeiCheck.com API.

        API endpoint (GET, no auth required for basic TAC lookup):
            https://alpha.imeicheck.com/api/modelBrandName?imei=<IMEI>&format=json

        If an API key is configured in Settings it is appended as:
            &key=<api_key>

        Response JSON (success example):
            {"model": "Galaxy S24", "brand": "Samsung", "name": "Samsung Galaxy S24"}

        Error codes returned by ImeiCheck.com:
            {"error": "Invalid IMEI"}  — bad IMEI length / format
            {"error": "Not found"}     — TAC not in database (rare)
        """
        api_enabled = self._get_bool_config('get_api_details')
        if not api_enabled:
            raise UserError(_(
                "IMEI device details lookup is not enabled. "
                "Please enable it under Mobile Service → Configuration → Settings."
            ))

        if not self.imei_no or len(self.imei_no) != 15 or not self.imei_no.isdigit():
            raise UserError(_(
                "Please enter a valid 15-digit IMEI number before fetching device details."
            ))

        api_key = self._get_config_param('api_key')
        api_username = self._get_config_param('api_username')
        api_url_slug = self._get_config_param('api_url_slug')
        api_php_service_id = self._get_config_param('api_php_service_id')

        if api_key and api_php_service_id:
            res = self._imeicheck_php_lookup(api_key, api_php_service_id)
        else:
            res = self._imeicheck_tac_lookup(api_key, api_username, api_url_slug)

        # Handle API-level errors
        if isinstance(res, dict) and res.get('error'):
            error_msg = res['error']
            if 'invalid' in error_msg.lower() or 'imei' in error_msg.lower():
                raise UserError(_("Invalid IMEI number. Please check and try again."))
            elif 'not found' in error_msg.lower():
                raise UserError(_(
                    "Device not found in ImeiCheck.com database. "
                    "The IMEI is valid but its TAC may not be listed yet."
                ))
            else:
                raise UserError(_("ImeiCheck.com error: %(msg)s", msg=error_msg))

        # Parse successful response
        # ImeiCheck.com returns: {"model": "...", "brand": "...", "name": "..."}
        # It may also return a plain string "Brand Model" for simple lookups
        if isinstance(res, str):
            # Fallback: plain text response — use as device name
            self.device_name = res
            self.manufacturer = res.split()[0] if res else ''
            _logger.warning("ImeiCheck.com returned plain string: %s", res)
            return

        response_brand = res.get('brand', res.get('manufacturer', ''))
        response_model = res.get('model', res.get('model_name', ''))
        response_name = res.get('name', res.get('modelName', res.get('device_name', '')))

        if not response_brand and not response_model:
            raise UserError(_(
                "ImeiCheck.com returned an empty result for this IMEI. "
                "The device TAC may not be in their database."
            ))

        self.device_name = response_name or f"{response_brand} {response_model}".strip()
        self.manufacturer = response_brand

        # Auto-create or link brand/model records
        self._link_or_create_brand_model(response_brand, response_model)

    def _imeicheck_php_lookup(self, api_key, service_id):
        """Use ImeiCheck PHP API when a PHP LIST service ID is configured."""
        params = {
            'key': api_key,
            'service': service_id,
            'imei': self.imei_no,
        }
        url = "https://alpha.imeicheck.com/api/php-api/create?%s" % (
            urllib.parse.urlencode(params)
        )
        res = self._imeicheck_request_json(url, api_key)
        status = str(res.get('status', '')).lower() if isinstance(res, dict) else ''
        if status in ('failed', 'error'):
            message = (
                res.get('response')
                or res.get('result')
                or res.get('message')
                or res.get('status')
                or _('Unknown error')
            )
            lower_message = str(message).lower()
            if 'wrong ip' in lower_message:
                raise UserError(_(
                    "ImeiCheck PHP API rejected this server IP. "
                    "Go to your ImeiCheck API Manage page and either reset the linked IP "
                    "or disable IP protection, then try again."
                ))
            if 'invalid apikey' in lower_message or 'invalid api key' in lower_message:
                raise UserError(_("ImeiCheck PHP API rejected the configured API key."))
            if 'credit' in lower_message:
                raise UserError(_("ImeiCheck PHP API reports insufficient credit for this request."))
            raise UserError(_("ImeiCheck PHP API error: %(msg)s", msg=message))
        if isinstance(res, dict) and isinstance(res.get('object'), dict):
            return res['object']
        if isinstance(res, dict) and res.get('result'):
            return {
                'name': res.get('result', ''),
                'model': res.get('result', ''),
                'brand': '',
            }
        return res

    def _imeicheck_tac_lookup(self, api_key, api_username, api_url_slug):
        """Use the public TAC lookup endpoint."""
        params = {
            'imei': self.imei_no,
            'format': 'json',
        }
        if api_key:
            params['key'] = api_key
        if api_username:
            params['username'] = api_username
        if api_url_slug:
            params['url'] = api_url_slug
        url = "https://alpha.imeicheck.com/api/modelBrandName?%s" % (
            urllib.parse.urlencode(params)
        )
        res = self._imeicheck_request_json(url, api_key)
        if isinstance(res, dict) and isinstance(res.get('object'), dict):
            return res['object']
        return res

    def _imeicheck_request_json(self, url, api_key):
        """Execute request and decode a JSON response from ImeiCheck."""
        _logger.info("IMEI lookup request: %s", url.replace(api_key or '', '***'))

        try:
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '
                                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                                  'Chrome/136.0.0.0 Safari/537.36',
                    'Accept': 'application/json,text/plain,*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
                },
            )

            with urllib.request.urlopen(req, timeout=15) as response:
                raw = response.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            error_body = ''
            try:
                error_body = e.read().decode('utf-8', errors='ignore')
            except Exception:
                pass
            if e.code == 403 and (
                'cf-mitigated' in error_body.lower()
                or 'just a moment' in error_body.lower()
                or 'enable javascript and cookies to continue' in error_body.lower()
            ):
                raise UserError(_(
                    "ImeiCheck.com blocked the lookup with a Cloudflare challenge. "
                    "If you have API Manage access, configure a PHP Service ID in Settings so "
                    "the module can use the PHP API instead of the public TAC endpoint."
                ))
            raise UserError(_(
                "ImeiCheck.com returned HTTP %(code)s. "
                "Please verify your API key in Settings or try again later.\n"
                "Detail: %(detail)s",
                code=e.code, detail=str(e.reason),
            ))
        except urllib.error.URLError as e:
            raise UserError(_(
                "Could not reach ImeiCheck.com. "
                "Please check your internet connection.\nDetail: %(detail)s",
                detail=str(e.reason),
            ))

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            raise UserError(_(
                "ImeiCheck.com returned an unexpected response. "
                "Please try again or contact support."
            ))

    def _link_or_create_brand_model(self, brand_name, model_name):
        """Find or create mobile.brand + brand.model and link to this service record."""
        BrandModel = self.env['brand.model']
        MobileBrand = self.env['mobile.brand']

        # Check if model already exists for this brand
        existing = BrandModel.search([
            ('mobile_brand_models', '=', model_name),
            ('mobile_brand_name.brand_name', '=', brand_name),
        ], limit=1)

        if existing:
            self.model_name = existing
            self.brand_name = existing.mobile_brand_name
            return

        # Find or create the brand
        brand_rec = MobileBrand.search([('brand_name', '=', brand_name)], limit=1)
        if not brand_rec:
            brand_rec = MobileBrand.create({'brand_name': brand_name})
            _logger.info("Auto-created mobile brand: %s", brand_name)

        # Create the model
        new_model = BrandModel.create({
            'mobile_brand_name': brand_rec.id,
            'mobile_brand_models': model_name,
        })
        _logger.info("Auto-created brand model: %s / %s", brand_name, model_name)

        self.model_name = new_model
        self.brand_name = brand_rec
