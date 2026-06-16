from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

    is_self_invoice = fields.Boolean(
        string="Self Invoice"
    )
    self_invoice_document_type = fields.Selection([
        ('TD01', 'TD01'),
        ('TD26', 'TD26'),
        ('TD17', 'TD17'),
    ], default='TD26')

    @api.depends('is_self_invoice', 'self_invoice_document_type')
    def _compute_l10n_it_document_type(self):
        super()._compute_l10n_it_document_type()
        for move in self:
            if move.is_self_invoice and move.self_invoice_document_type:
                doc_type = self.env['l10n_it.document.type'].search([
                    ('code', '=', move.self_invoice_document_type)
                ], limit=1)
                if doc_type:
                    move.l10n_it_document_type = doc_type

    def _l10n_it_edi_get_values(self, pdf_values=None):
        values = super()._l10n_it_edi_get_values(pdf_values=pdf_values)
        if self.is_self_invoice:
            values['is_custom_self_invoice'] = True
        return values