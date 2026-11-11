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
from odoo import http
from odoo.http import request
try:
    from odoo.http.stream import content_disposition
except ImportError:
    from odoo.http import content_disposition
try:
    from odoo.http.dispatcher import serialize_exception as _serialize_exception
except ImportError:
    from odoo.http import serialize_exception as _serialize_exception
from odoo.tools import html_escape


class XLSXReportController(http.Controller):
    """This model is used to connect the frontend to the backend"""

    @http.route('/bank_xlsx_reports', type='http', auth='user',
                methods=['POST'], csrf=False)
    def get_report_xlsx(self, options, output_format, report_name):
        """This function is called when a post request is made to this route"""
        uid = request.session.uid
        report_obj = request.env[
            'report.base_accounting_kit.report_bank_book'].with_user(uid)
        options = json.loads(options)
        token = 'dummy-because-api-expects-one'
        try:
            if output_format == 'xlsx':
                response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition',
                         content_disposition(report_name + '.xlsx'))
                    ]
                )
                report_obj.get_xlsx_report(options, response)
            response.set_cookie('fileToken', token)
            return response
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': 'Odoo Server Error',
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))
