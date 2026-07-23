from odoo import api, fields, models

class ProductTemplateAttributeLine(models.Model):
    _inherit = "product.template.attribute.line"

    attribute_idd = fields.Many2one('saved.attributes', string="Attribute")


    def save_preset(self):
        preset = self.env['saved.attributes'].create({
            'name': f"{self.attribute_id.name} Preset",
            'attribute_id': self.attribute_id.id,
            'value_ids': self.value_ids.ids,
        })

    @api.onchange('attribute_idd')
    def onchange_id(self):
        print(self.attribute_idd.name)
        print(self.attribute_idd.attribute_id)
        print(self.attribute_idd.value_ids)
        self.attribute_id = self.attribute_idd.attribute_id
        self.value_ids = self.attribute_idd.value_ids.ids
