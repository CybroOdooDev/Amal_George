# -*- coding: utf-8 -*-
################################################################################
#
#    Mobile Service Management Pro — Odoo 19
#    Controller: XLSX report download endpoint
#
#    Odoo 19 change: http.serialize_exception → werkzeug / traceback handling
#
################################################################################
import json
import traceback
from odoo import http
from odoo.http import content_disposition, request
from odoo.tools import html_escape


class XLSXReportController(http.Controller):
    """HTTP controller that serves generated XLSX reports as file downloads.

    The JavaScript action_manager.js intercepts 'service_xlsx' report actions
    and POSTs to this endpoint instead of the standard PDF pipeline.
    """

    @http.route(
        '/mobile_service_xlsx_reports',
        type='http',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def get_report_xlsx(self, model, options, output_format, report_name, **kwargs):
        """Generate and stream an XLSX file back to the browser."""
        uid = request.session.uid
        report_obj = request.env[model].with_user(uid)
        options = json.loads(options)
        try:
            if output_format == 'xlsx':
                response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type',
                         'application/vnd.openxmlformats-officedocument'
                         '.spreadsheetml.sheet'),
                        ('Content-Disposition',
                         content_disposition(report_name + '.xlsx')),
                    ],
                )
                report_obj.get_xlsx_report(options, response)
                response.set_cookie('fileToken', 'dummy-because-api-expects-one')
                return response
        except Exception:
            error = {
                'code': 200,
                'message': 'Odoo Server Error',
                'data': traceback.format_exc(),
            }
            return request.make_response(
                html_escape(json.dumps(error)),
                headers=[('Content-Type', 'application/json')],
            )
