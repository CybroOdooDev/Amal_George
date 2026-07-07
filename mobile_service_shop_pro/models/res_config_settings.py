# -*- coding: utf-8 -*-
################################################################################
#
#    Mobile Service Management Pro — Odoo 19
#    Configuration settings model
#
################################################################################
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Extends res.config.settings with Mobile Service Pro configuration:
    - ImeiCheck.com API key and toggle
    - Show/hide complaints on printed tickets
    """
    _inherit = 'res.config.settings'

    api_key = fields.Char(
        string="ImeiCheck API Key",
        help=(
            "Personal API key from ImeiCheck.com.\n"
            "Register at https://imeicheck.com and contact them to obtain "
            "a free key with 60 requests/minute.\n"
            "Leave blank to use the public endpoint (may be CAPTCHA-protected)."
        ),
        config_parameter="mobile_service_shop_pro.api_key",
    )
    api_username = fields.Char(
        string="ImeiCheck Username",
        help=(
            "Optional username/account name supplied by ImeiCheck.com. "
            "If set, it is forwarded with the lookup request."
        ),
        config_parameter="mobile_service_shop_pro.api_username",
    )
    api_url_slug = fields.Char(
        string="ImeiCheck URL",
        help=(
            "Optional URL or account slug supplied by ImeiCheck.com. "
            "For example: 'vishnuraj'. If set, it is forwarded with the "
            "lookup request."
        ),
        config_parameter="mobile_service_shop_pro.api_url_slug",
    )
    api_php_service_id = fields.Char(
        string="ImeiCheck PHP Service ID",
        help=(
            "Optional service ID from the ImeiCheck.com PHP LIST page. "
            "When set, Odoo will use the PHP API endpoint instead of the "
            "public TAC endpoint."
        ),
        config_parameter="mobile_service_shop_pro.api_php_service_id",
    )
    get_api_details = fields.Boolean(
        string="IMEI Device Details",
        help=(
            "Enable this to allow technicians to auto-fill device brand and model "
            "by entering the IMEI number and clicking 'Get Details'.\n"
            "Requires a valid ImeiCheck.com API key."
        ),
        config_parameter="mobile_service_shop_pro.get_api_details",
    )
    show_complain_types = fields.Boolean(
        string="Show Complaints on Ticket",
        help=(
            "When enabled, complaint types and descriptions are printed "
            "on the customer service ticket PDF."
        ),
        config_parameter="mobile_service_shop_pro.show_complain_types",
    )
