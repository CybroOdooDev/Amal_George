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
{'name': 'Salon Management for Odoo Online',
 'version': 'saas~19.4.1.0',
 'category': 'Services',
 'summary': 'Manage salon operations, service packages, client appointments (bookings), active resources (chairs), beautician schedules, and automatic invoicing.',
 'description': """
Salon Management SaaS Module
============================
A comprehensive solution for managing salon and beauty center operations.

Key Features:
-------------
* **Interactive Booking Portal**: A public-facing portal (/salon-booking) for clients to book services or packages, pick slots, and select beauticians.
* **Resources & Chair Scheduling**: Manage active booking resources (Chairs) with automated assignment and overlap prevention checks.
* **Double Booking Prevention**: Validations to ensure beauticians (employees) and chairs are not booked for overlapping time slots.
* **Holidays & Company Breaks**: Restrict client bookings on customized holidays, weekly recurring off-days, and during company break hours.
* **Service Packages**: Bundle multiple services with customizable discounts and automatic total price calculations.
* **Auto-Invoicing**: Automatically generates and links Odoo client invoices (account.move) upon completing or confirming salon appointments.
* **KPI Dashboard**: A modern, interactive dashboard tracking today's bookings, monthly revenue, active chairs, and employee stats.
* **Guest Bookings**: Public users can book online, automatically creating or linking contact profiles in the database.
""",
 'author': 'Cybrosys Techno Solutions',
 'company': 'Cybrosys Techno Solutions',
 'maintainer': 'Cybrosys Techno Solutions',
 'website': 'https://www.cybrosys.com',
 'depends': ['account_reports', 'hr', 'hr_skills', 'web_grid', 'web_studio', 'website'],
 'data': ['data/ir_model.xml',
          'data/ir_model_fields.xml',
          'data/mail_templates.xml',
          'data/ir_actions_act_window.xml',
          'data/ir_actions_server.xml',
          'data/ir_ui_view.xml',
          'data/ir_ui_menu.xml',
          'data/base_automation.xml',
          'data/ir_access.xml',
          'data/ir_sequence_data.xml',
          'data/ir_default.xml',
          'data/report_booking.xml',
          'data/website_booking_templates.xml',
          'data/website_form_whitelist.xml'],
 'assets': {
     'web.assets_backend': [
         'salon_management_saas/static/src/js/salon_dashboard.js',
         'salon_management_saas/static/src/xml/salon_dashboard.xml',
     ],
     'web.assets_frontend': [
         'salon_management_saas/static/src/js/website_booking.js',
     ]
 },
 'license': 'OPL-1',
 'application': True,
 'installable': True}