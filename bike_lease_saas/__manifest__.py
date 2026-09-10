###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Amal George (odoo@cybrosys.com)
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
################################################################################
{
    'name': 'Bike Lease Management for Odoo Online',
    'version': 'saas~19.4.1.0',
    'category': 'Industries',
    'summary': 'Comprehensive Bike Lease SaaS Management Application for Odoo Online 19.4',
    'description': """Bike Lease Management for Odoo Online SaaS 19.4, featuring an interactive analytics dashboard, customizable lease plans, customer application pipelines, automated lease contracts, itemized installment schedules with daily vehicle surcharges, return inspection net deposit settlements, bike fleet vehicle inventory, and maintenance service logs.""",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    'depends': [
        'base',
        'account',
        'fleet',
        'mail',
        'stock',
        'base_automation',
        'web_grid',
        'web_studio',
    ],
    'data': [
        'data/ir_sequence.xml',
        'data/ir_model.xml',
        'data/ir_model_fields.xml',
        'data/fleet_vehicle_state_data.xml',
        'data/mail_templates.xml',
        'data/ir_actions_server.xml',
        'data/ir_actions_act_window.xml',
        'data/ir_actions_client.xml',
        'data/ir_ui_view.xml',
        'data/ir_ui_menu.xml',
        'data/ir_access.xml',
        'data/ir_default.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bike_lease_saas/static/src/css/dashboard.css',
            'bike_lease_saas/static/src/xml/dashboard.xml',
            'bike_lease_saas/static/src/js/dashboard.js',
        ],
    },
    'images': ['static/description/banner.jpg'],
    'license': 'OPL-1',
    'application': True,
    'installable': True,
}
