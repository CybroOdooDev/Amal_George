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
import base64
import logging
import mimetypes
import requests
from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


class OraFile(models.Model):
    """Used to store custom files."""
    _name = "ora.file"
    _description = "Ora File"

    name = fields.Char(string="Name", required=True,
                       help="A descriptive name for the file.")
    file = fields.Binary(string="File", required=True,
                         help="The actual binary file to be stored.")
    id_file = fields.Char(string="File id", readonly=True,
                          help="The unique identifier of the file.")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('uploaded', 'Uploaded'),
        ('error', 'Error')
    ], string="Status", default='draft', readonly=True)
    error_message = fields.Text(string="Error Details", readonly=True)
    company_id = fields.Many2one('res.company', string="Company",
                                 default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        """Create a new OraFile record and upload the file to VAPI."""
        bearer = self.env['ir.config_parameter'].sudo().get_str(
            'ora_ai_base.vapi_private_api_key')
        records = super().create(vals_list)
        for res in records:
            if not res.file:
                continue
            decoded_data = base64.b64decode(res.file)
            if len(decoded_data) > MAX_FILE_SIZE:
                raise ValidationError("File size exceeds maximum allowed size (25MB).")

            # Detect dynamic MIME type
            mime_type, _ = mimetypes.guess_type(res.name or '')
            if not mime_type:
                mime_type = "application/octet-stream"

            if bearer:
                url = "https://api.vapi.ai/file"
                files = {
                    "file": (res.name, decoded_data, mime_type)
                }
                headers = {
                    "Authorization": f"Bearer {bearer}"
                }
                try:
                    response = requests.post(url, files=files, headers=headers, timeout=30)
                    json_response = response.json()
                    if response.ok and json_response.get('id'):
                        res.write({
                            'id_file': json_response.get('id'),
                            'state': 'uploaded',
                            'error_message': False
                        })
                    else:
                        err = json_response.get('message') or response.text
                        res.write({'state': 'error', 'error_message': f"Vapi Error: {err}"})
                except Exception as e:
                    _logger.exception("Failed to upload file to Vapi: %s", e)
                    res.write({'state': 'error', 'error_message': str(e)})
        return records

    def unlink(self):
        """Delete OraFile record and remove the associated file from VAPI."""
        bearer = self.env['ir.config_parameter'].sudo().get_str(
            'ora_ai_base.vapi_private_api_key')
        for rec in self:
            if rec.id_file and bearer:
                url = f"https://api.vapi.ai/file/{rec.id_file}"
                headers = {"Authorization": f"Bearer {bearer}"}
                try:
                    requests.delete(url, headers=headers, timeout=10)
                except Exception as e:
                    _logger.warning("Failed to delete file %s from Vapi: %s", rec.id_file, e)
        return super().unlink()

    def write(self, vals):
        """Update the OraFile record and propagate changes to VAPI."""
        bearer = self.env['ir.config_parameter'].sudo().get_str(
            'ora_ai_base.vapi_private_api_key')
        res = super().write(vals)
        if 'name' in vals:
            for rec in self:
                if rec.id_file and bearer:
                    url = f"https://api.vapi.ai/file/{rec.id_file}"
                    payload = {"name": rec.name}
                    headers = {
                        "Authorization": f"Bearer {bearer}",
                        "Content-Type": "application/json"
                    }
                    try:
                        requests.patch(url, json=payload, headers=headers, timeout=10)
                    except Exception as e:
                        _logger.warning("Failed to rename file %s on Vapi: %s", rec.id_file, e)
        return res
