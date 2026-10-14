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
from markupsafe import Markup

from odoo import fields, models, _
from odoo.exceptions import UserError


class SaleStockReservation(models.TransientModel):
    """
    This model is used to reserve products for a sale order.

    Fields:
    - stock_reservation_ids: A one-to-many relationship to the
     `stock.reservation` model, representing the reservations to be made.
    - sale_order_id: The ID of the sale order for which the products are being
      reserved.
    - partner_id: The customer linked to the sale quotation.
    - mail_notification_ids: A many-to-many relationship to the `res.users`
      model,representing the users who should receive email notifications about
      the reservation.
    """
    _name = "sale.stock.reservation"
    _description = "Stock Reservation"

    stock_reservation_ids = fields.One2many(
        "stock.reservation",
        "stock_reservation_wizard_id",
        string="Order line",
        help='This is a One2many field that refers to the reserved stock items '
             'associated with the wizard.')
    sale_order_id = fields.Many2one(
        "sale.order", string="Sale order",
        readonly=True,
        help="Many2one field that returns the Sale Order")
    partner_id = fields.Many2one(
        "res.partner", string="Customer",
        related="sale_order_id.partner_id",
        readonly=True,
        help="Customer linked to the sale quotation")
    mail_notification_ids = fields.Many2many(
        "res.users",
        string="Email Notification",
        help='This is a Many2many field that refers to the users '
             'who will receive email notifications.')

    def action_reserve_stock(self):
        self.ensure_one()

        sale_order = self.sale_order_id
        if not sale_order:
            raise UserError("No sale order linked to this reservation.")

        # Set reservation state on sale order
        sale_order.state_reservation = "reserved"

        # Standard virtual customer location (reduces forecasted stock)
        customer_loc = self.env.ref('stock.stock_location_customers')

        # Get warehouse and picking type
        warehouse = sale_order.warehouse_id
        if not warehouse or not warehouse.lot_stock_id:
            raise UserError("Please configure a warehouse with stock location on the sale order.")

        picking_type = warehouse.out_type_id
        if not picking_type:
            raise UserError("No outgoing picking type configured on the warehouse.")

        company = sale_order.company_id

        # Prepare history lines
        history_vals_list = []

        for rec in self.stock_reservation_ids:
            # Safely convert reserve_quantity to float (fixes str vs int error)
            try:
                reserve_qty = float(rec.reserve_quantity or 0)
            except (ValueError, TypeError):
                reserve_qty = 0.0
            if reserve_qty <= 0:
                continue
            move_vals = {
                'product_id': rec.product_id.id,
                'product_uom_qty': reserve_qty,
                'product_uom': rec.unit_of_measure_id.id,
                'location_id': warehouse.lot_stock_id.id,
                'location_dest_id': customer_loc.id,
                'picking_type_id': picking_type.id,
                'company_id': company.id,
                'date': fields.Datetime.now(),
                'origin': sale_order.name,

            }
            move = self.env['stock.move'].create(move_vals)
            rec.move_id = move.id
            move._action_confirm()
            self.env['stock.move.line'].create({
                'move_id': move.id,
                'product_id': rec.product_id.id,
                'product_uom_id': rec.unit_of_measure_id.id,
                'location_id': warehouse.lot_stock_id.id,
                'location_dest_id': customer_loc.id,
                'quantity': reserve_qty,
            })
            history_vals_list.append((0, 0, {
                'order_line_name': rec.order_line_name,
                'product_id': rec.product_id.id,
                'reserved_quantity': reserve_qty,
                'sale_order_id': sale_order.id,
                'status': 'reserved',
                'move_id': move.id,
            }))
        if history_vals_list:
            sale_order.write({'reserved_stock_ids': history_vals_list})

        reserved_lines = sale_order.reserved_stock_ids.filtered(lambda r: r.status == 'reserved')
        if reserved_lines:
            table_rows = "".join(
                f"<tr>"
                f"<td style='padding: 8px;'>{line.order_line_name or line.product_id.display_name}</td>"
                f"<td style='padding: 8px;'>{line.product_id.name}</td>"
                f"<td style='padding: 8px;'>{line.reserved_quantity}</td>"
                f"</tr>"
                for line in reserved_lines
            )

            table_html = (
                f"<table border='1' cellpadding='8' cellspacing='0' style='border-collapse: collapse; width: 100%; border: 1px solid #dee2e6;'>"
                f"<tr style='background-color: #ededed; text-align: left;'>"
                f"<th style='padding: 8px;'>Line</th>"
                f"<th style='padding: 8px;'>Product</th>"
                f"<th style='padding: 8px;'>Reserved Quantity</th>"
                f"</tr>"
                f"{table_rows}"
                f"</table>"
            )

            email_from = company.email or self.env.user.email or 'no-reply@yourcompany.com'
            customer = sale_order.partner_id
            customer_email = customer.email or (customer.commercial_partner_id and customer.commercial_partner_id.email) if customer else False

            # Send stock reservation email to the customer (single email via email_to)
            if customer and customer_email:
                customer_message_body = (
                    f"<p>Dear {customer.name},</p>"
                    f"<p>We would like to inform you that some item(s) have been reserved for your quotation "
                    f"<strong>{sale_order.name}</strong>.</p>"
                    f"{table_html}"
                    f"<p>Thank you.</p>"
                )

                customer_mail_values = {
                    'subject': f"Stock Reservation: {sale_order.name}",
                    'body_html': customer_message_body,
                    'email_from': email_from,
                    'email_to': customer_email,
                }
                self.env['mail.mail'].create(customer_mail_values).send()
            elif customer and not customer_email:
                sale_order.message_post(
                    body=Markup(_(
                        "<p>Stock reservation was created, but notification email could not be sent because "
                        "customer <strong>%s</strong> has no email address configured.</p>"
                    ) % customer.name)
                )

            # Send email notification to selected internal users if specified
            if self.mail_notification_ids:
                user_emails = [u.email or u.login for u in self.mail_notification_ids if (u.email or u.login)]
                if user_emails:
                    user_message_body = (
                        f"<p>Dear {', '.join(self.mail_notification_ids.mapped('name'))},</p>"
                        f"<p>We would like to inform you that some item(s) have been reserved for "
                        f"<strong>{sale_order.name}</strong>"
                        f"{f' (Customer: {customer.name})' if customer else ''}.</p>"
                        f"{table_html}"
                        f"<p>Thank you.</p>"
                    )

                    users_mail_values = {
                        'subject': f"Stock Reservation Notification: {sale_order.name}",
                        'body_html': user_message_body,
                        'email_from': email_from,
                        'email_to': ", ".join(user_emails),
                    }
                    self.env['mail.mail'].create(users_mail_values).send()

            # Post a clear, permanent confirmation note in the sale order chatter
            chatter_body = (
                f"<p><strong>Stock Reservation Confirmed</strong></p>"
                f"<p>The following item(s) have been reserved for quotation <strong>{sale_order.name}</strong>:</p>"
                f"{table_html}"
            )
            if customer and customer_email:
                chatter_body += f"<p><small class='text-muted'>Notification email sent to customer: {customer.name} ({customer_email})</small></p>"
            if self.mail_notification_ids:
                user_names = ", ".join(self.mail_notification_ids.mapped('name'))
                chatter_body += f"<p><small class='text-muted'>Notification email sent to user(s): {user_names}</small></p>"

            sale_order.message_post(
                body=Markup(chatter_body),
                subject=f"Stock Reservation: {sale_order.name}",
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

        return True



