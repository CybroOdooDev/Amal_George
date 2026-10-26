from odoo import api, fields, models
from odoo import Command


class SaleOrder(models.Model):
    _inherit = "sale.order"

    multi_delivery = fields.Boolean(default=False, string="Multi Delivery")

    def action_confirm(self):
        if self.multi_delivery:
            print("Multi Delivery")
            print(self.order_line.read())
            move_lines=[]
            tmpl_ids = self.order_line.product_id.mapped('product_tmpl_id')
            print("tmpl ids:",tmpl_ids)
            for tmpl_id in tmpl_ids:
                for line in self.order_line:
                    if line.product_id.product_tmpl_id == tmpl_id :
                        move_lines.append(Command.create({
                            'product_id': line.product_id.id,
                            'quantity': line.product_uom_qty,
                        }))

                self.picking_ids += self.env['stock.picking'].create({
                    'partner_id': self.partner_id.id,
                    'state': 'confirmed',
                    'picking_type_id': self.warehouse_id.out_type_id.id,
                    'move_line_ids': move_lines
                })
                move_lines = []
                print(self.picking_ids)

                self.state = "sale"
                print(self.warehouse_id.read())

        else:
            res = super().action_confirm()
            return res
