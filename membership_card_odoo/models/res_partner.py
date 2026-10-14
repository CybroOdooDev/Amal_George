# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Technologies (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC
#    LICENSE (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import _, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    """Inherit res.partner to add membership card fields and card printing
    action. In Odoo 19 the old membership module was removed, so these
    fields are now defined directly in this module."""

    _inherit = 'res.partner'

    # --- Membership fields (previously from the removed membership module) ---
    free_member = fields.Boolean(
        string='Free Member',
        default=False,
        help="Check if this partner is a free/honorary member "
             "who does not need to purchase a membership product."
    )
    member_lines = fields.One2many(
        'membership.card.line',
        'partner_id',
        string='Membership Lines',
        help="Membership product lines associated with this partner."
    )

    def server_action_get_card(self):
        """Fetch data from res.partner to pass into the membership card
        report template and trigger the PDF report action."""
        self.ensure_one()
        if not self.image_1920:
            raise ValidationError(
                _("Please provide an image for '%s' before generating the membership card.", self.name)
            )
        if not self.phone:
            raise ValidationError(
                _("Please provide a phone number for '%s' before generating the membership card.", self.name)
            )
        start_date = False
        end_date = False
        membership_products = []

        if not self.free_member:
            # 1. Check if the partner has any membership plan configured
            lines_with_plan = self.member_lines.filtered(lambda l: l.membership_id)
            if not lines_with_plan:
                raise ValidationError(
                    _("Partner '%s' does not have a membership plan. Please add a membership product to print the card.", self.name)
                )

            # 2. Check if the partner is currently in a valid membership period
            today = fields.Date.context_today(self)
            active_lines = lines_with_plan.filtered(
                lambda l: (not l.date_from or l.date_from <= today) and (not l.date_to or today <= l.date_to)
            )
            if not active_lines:
                expired_lines = lines_with_plan.filtered(lambda l: l.date_to and l.date_to < today)
                future_lines = lines_with_plan.filtered(lambda l: l.date_from and l.date_from > today)
                if expired_lines and not future_lines:
                    raise ValidationError(
                        _("The membership for '%s' expired on %s. Cannot print membership card for an expired membership.",
                          self.name, expired_lines[0].date_to)
                    )
                elif future_lines and not expired_lines:
                    raise ValidationError(
                        _("The membership for '%s' starts on %s. Cannot print membership card before the membership period begins.",
                          self.name, future_lines[0].date_from)
                    )
                else:
                    raise ValidationError(
                        _("Partner '%s' is not within an active membership period today (%s).",
                          self.name, today)
                    )

            active_line = active_lines[0]
            start_date = active_line.date_from
            end_date = active_line.date_to
            membership_products = [active_line.membership_id.name]

            if start_date and end_date and end_date < start_date:
                raise ValidationError(
                    _("End Date (%s) cannot be earlier than Start Date (%s).",
                      end_date, start_date)
                )

        company_id = self.env.company
        image_data = self.image_1920.decode('utf-8') if isinstance(self.image_1920, bytes) else (self.image_1920 or '')

        data = {
            'name': self.name,
            'image': image_data,
            'phone': self.phone,
            'function': self.function,
            'free_member': self.free_member,
            'membership_product': membership_products,
            'start_date': start_date,
            'end_date': end_date,
            'company_name': company_id.name,
            'company_address': company_id.street,
            'city': company_id.city,
            'country': company_id.country_id.name,
            'state': company_id.state_id.name,
            'company_email': company_id.email,
            'company_phone': company_id.phone,
            'website': company_id.website,
        }
        return (
            self.env.ref('membership_card_odoo.action_membership_card')
            .report_action(None, data=data)
        )
