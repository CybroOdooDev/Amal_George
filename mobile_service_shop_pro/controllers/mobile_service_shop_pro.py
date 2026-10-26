# -- coding: utf-8 --
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Technologies(odoo@cybrosys.com)
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
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

import json
import traceback
from odoo import http
from odoo.http import content_disposition, request


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
                json.dumps(error),
                status=400,
                headers=[('Content-Type', 'application/json')],
            )


