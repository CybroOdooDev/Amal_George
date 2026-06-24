from odoo import api, fields, models, tools


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            if move.partner_id and (not move.name or move.name == '/'):
                move.name = move.partner_id._next_autoinv_number()
        return moves

    def _compute_name(self):
        """Keep the custom number assigned at create.

        Core ``_compute_name`` resets a draft move's name to ``False`` when it
        doesn't match the journal's date-based sequence (account_move.py:946),
        which wiped our custom number on save. Skip moves that already carry a
        custom number so it persists on draft and after posting.
        """
        custom = self.filtered(lambda m: m.name and m.name != '/')
        return super(AccountMove, self - custom)._compute_name()

    def _must_check_constrains_date_sequence(self):
        """Custom autoinv numbers (e.g. A09/26) aren't date-based, so skip
        Odoo's date-vs-sequence alignment constraint that blocks posting."""
        return False
