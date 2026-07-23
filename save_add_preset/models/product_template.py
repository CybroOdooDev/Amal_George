from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"


    attribute_idd = fields.Many2one('saved.attributes', string="Attribute")

