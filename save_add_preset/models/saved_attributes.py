from odoo import api, fields, models

class SavedAttributes(models.Model):
    _name = 'saved.attributes'
    _description = 'Saved Attributes'

    name = fields.Char(string='Name', required=True)
    attribute_id = fields.Many2one('product.attribute', string='Attribute', required=True)
    value_ids = fields.Many2many('product.attribute.value', string='Values')
