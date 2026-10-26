# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <https://www.gnu.org/licenses/>.
#
#############################################################################

# Field defaults are only applied to rows that exist when the column is first
# created, so companies predating these columns (or predating their defaults)
# kept a zero score. Zero is not a valid threshold: it passes every vendor
# audit and every training assessment. Backfill those rows with the field
# defaults so the new 0 < score <= 100 constraint holds everywhere.
DEFAULTS = {
    'pharma_vendor_approval_percentage': 70.0,
    'pharma_training_passing_score': 80.0,
}


def migrate(cr, version):
    """Replace zero or missing pharma scores on existing companies."""
    for column, default in DEFAULTS.items():
        cr.execute(
            """
                UPDATE res_company
                   SET %(column)s = %%s
                 WHERE %(column)s IS NULL
                    OR %(column)s <= 0
                    OR %(column)s > 100
            """ % {'column': column},
            (default,),
        )