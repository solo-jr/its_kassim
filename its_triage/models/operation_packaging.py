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

from odoo import fields, models, api, _


class OperationPackaging(models.Model):
    _name = "operation.packaging"
    _description = "Packaging"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Number', required=True, copy=False, default='/')
    product_id = fields.Many2one('product.product', string='Product', check_company=True)
    line_ids = fields.One2many('operation.packaging.line', 'packaging_id', string='Lines')

    @api.model
    def default_get(self, fields):
        res = super(OperationPackaging, self).default_get(fields)
        res['line_ids'] = [[0, 0, {'bag_capacity_id': rec.id, 'quantity': 0}] for rec in
                           self.env['operation.capacity'].sudo().search([])]
        return res

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('packaging')
        res = super(OperationPackaging, self).create(values)
        return res

    def action_update_quantity_on_hand(self):
        """
        Update quantity on hand for the current selected product
        :rtype: object
        """
        return {
            'name': _('Update Quantity'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'update.quantity.wizard',
            'target': 'new',
        }


class OperationPackagingLine(models.Model):
    _name = "operation.packaging.line"
    _description = "Triage Line"

    packaging_id = fields.Many2one('operation.packaging', string='Packaging', index=True)
    bag_capacity_id = fields.Many2one('operation.capacity', string='Bag Capacity')
    quantity = fields.Float("Quantity", digits='Product Unit of Measure', required=True)
