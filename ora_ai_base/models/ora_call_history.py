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
from odoo import api, fields, models


class OraCallHistory(models.Model):
    """Stores call logs, transcripts, and metadata for voice assistant sessions."""
    _name = "ora.call.history"
    _description = "Voice Assistant Call History"
    _order = "create_date desc"
    _rec_name = "name"

    name = fields.Char(string="Reference", default=lambda self: self.env['ir.sequence'].next_by_code('ora.call.history') or 'Call')
    vapi_call_id = fields.Char(string="Vapi Call ID", index=True, copy=False, help="Unique identifier of the call assigned by Vapi.")
    assistant_id = fields.Many2one("ora.ai", string="Assistant", ondelete="set null")
    partner_id = fields.Many2one("res.partner", string="Customer", ondelete="set null")
    order_id = fields.Many2one("sale.order", string="Generated Sale Order", ondelete="set null")
    call_type = fields.Selection([
        ('inboundPhoneCall', 'Inbound Phone'),
        ('webCall', 'Web Call'),
        ('outboundPhoneCall', 'Outbound Phone'),
    ], string="Call Type", default='webCall')
    start_time = fields.Datetime(string="Start Time")
    end_time = fields.Datetime(string="End Time")
    duration = fields.Integer(string="Duration (seconds)", default=0)
    status = fields.Selection([
        ('started', 'Started'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], string="Call Status", default='started')
    transcript = fields.Text(string="Full Transcript")
    recording_url = fields.Char(string="Recording URL")
    cost = fields.Float(string="Call Cost", digits=(16, 4), default=0.0)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)
    currency_id = fields.Many2one("res.currency", string="Currency", related="company_id.currency_id", readonly=True)

    _uniq_vapi_call_id = models.Constraint('UNIQUE(vapi_call_id)', 'A call record with this Vapi Call ID already exists!')

    @api.model
    def log_call_status(self, data):
        """Processes incoming Vapi status updates or end-of-call reports idempotently."""
        if not data:
            return False

        message = data.get('message', {}) if isinstance(data, dict) else {}
        msg_type = message.get('type')
        call = message.get('call', {}) or {}
        call_id = call.get('id') or data.get('call_id') or message.get('call_id')
        if not call_id:
            return False

        record = self.sudo().search([('vapi_call_id', '=', call_id)], limit=1)

        call_type = call.get('type') or 'webCall'
        assistant_vapi_id = call.get('assistantId')
        assistant = False
        if assistant_vapi_id:
            assistant = self.env['ora.ai'].sudo().search([('id_assistant', '=', assistant_vapi_id)], limit=1)

        # Extract transcript if available
        raw_transcript = message.get('transcript') or call.get('transcript')
        if not raw_transcript:
            conv = message.get('conversation') or []
            if isinstance(conv, list):
                raw_transcript = "\n".join([f"{m.get('role', 'speaker')}: {m.get('content', '')}" for m in conv if isinstance(m, dict) and m.get('role') != 'system'])

        # Calculate duration or costs
        duration = 0
        costs = message.get('cost') or call.get('cost') or 0.0
        recording_url = message.get('recordingUrl') or call.get('recordingUrl') or False

        if call.get('startedAt') and call.get('endedAt'):
            # In Vapi ISO strings
            try:
                import dateutil.parser
                s_dt = dateutil.parser.isoparse(call['startedAt'])
                e_dt = dateutil.parser.isoparse(call['endedAt'])
                duration = int((e_dt - s_dt).total_seconds())
            except Exception:
                duration = int(call.get('duration') or 0)

        vals = {
            'call_type': call_type,
            'duration': duration or (record.duration if record else 0),
            'cost': float(costs) if costs else (record.cost if record else 0.0),
        }
        if assistant:
            vals['assistant_id'] = assistant.id
        if raw_transcript:
            vals['transcript'] = raw_transcript
        if recording_url:
            vals['recording_url'] = recording_url
        if msg_type == 'end-of-call-report' or message.get('endedReason'):
            vals['status'] = 'completed'

        if record:
            record.write(vals)
        else:
            vals.update({
                'vapi_call_id': call_id,
                'name': f"Call-{call_id[:8]}" if call_id else "Call",
                'status': 'completed' if msg_type == 'end-of-call-report' else 'started',
            })
            record = self.sudo().create(vals)

        return record
