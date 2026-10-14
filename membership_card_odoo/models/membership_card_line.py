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
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MembershipCardLine(models.Model):
    """Stores individual membership product lines for a partner.
    Replaces the removed membership.line model from the old membership
    module which no longer exists in Odoo 19."""

    _name = 'membership.card.line'
    _description = 'Membership Card Line'
    _order = 'date_from desc'

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        ondelete='cascade',
        required=True,
        help="The partner who holds this membership line."
    )
    membership_id = fields.Many2one(
        'product.template',
        required=True,
        string='Membership Product',
        help="The product/service representing the membership."
    )
    date_from = fields.Date(
        string='Start Date',
        required=True,
        help="Date from which the membership is valid."
    )
    date_to = fields.Date(
        string='End Date',
        required=True,
        help="Date until which the membership is valid."
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for line in self:
            if line.date_from and line.date_to and line.date_to < line.date_from:
                raise ValidationError(
                    _("End Date (%s) cannot be earlier than Start Date (%s).",
                      line.date_to, line.date_from)
                )
