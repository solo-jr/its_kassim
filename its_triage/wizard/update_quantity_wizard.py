# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2021 IT-Solutions.mg. All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import fields, models, api


class UpdateQtyWiz(models.TransientModel):
    """
        A wizard to manage the updating of quantity on hand.
    """

    _name = 'update.quantity.wizard'
    _description = 'Update Quantity'

    @api.model
    def default_get(self, values):
        res = super(UpdateQtyWiz, self).default_get(values)
        if self._context.get('active_id'):
            packaging_id = self.env['operation.packaging'].sudo().browse(self._context.get('active_id'))
            if packaging_id:
                res['product_id'] = packaging_id.product_id.id
                res['line_ids'] = [[0, 0, {
                    'bag_capacity_id': rec.bag_capacity_id.id,
                    'quantity': 0}] for rec in packaging_id.line_ids]
        return res

    product_id = fields.Many2one('product.product', string='Product', check_company=True)
    line_ids = fields.One2many('update.quantity.wizard.line', 'wiz_id', string='Lines')

    def action_update(self):
        self.ensure_one()
        packaging_id = self.env['operation.packaging'].sudo().browse(self._context.get('active_id'))
        if packaging_id:
            for line in packaging_id.line_ids:
                line.quantity += self.line_ids.filtered(
                    lambda x: x.bag_capacity_id.id == line.bag_capacity_id.id).quantity
        return {'type': 'ir.actions.act_window_close'}


class UpdateQtyLineWiz(models.TransientModel):
    _name = 'update.quantity.wizard.line'
    _description = 'Update Quantity Line'

    wiz_id = fields.Many2one('update.quantity.wizard', string='Packaging', index=True)
    bag_capacity_id = fields.Many2one('operation.capacity', string='Bag Capacity')
    quantity = fields.Float("Quantity", digits='Product Unit of Measure', required=True)
