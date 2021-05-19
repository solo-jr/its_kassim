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


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    freight_charges = fields.Monetary(string='Freight Charges')
    docker_fees = fields.Monetary(string='Docker Fees')
    truck_number = fields.Char(string='Truck Number')

    @api.depends('order_line.price_total', 'freight_charges', 'docker_fees')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax + order.freight_charges + order.docker_fees,
            })


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    number_of_bags = fields.Integer(string='Number of Bags')
    bag_capacity_id = fields.Many2one('operation.capacity', string='Bag Capacity')

    @api.onchange('number_of_bags')
    def _onchange_number_of_bags(self):
        if self.number_of_bags and self.bag_capacity_id:
            self.product_qty = self.number_of_bags * self.bag_capacity_id.capacity

    @api.onchange('product_qty', 'product_uom', 'bag_capacity_id')
    def _onchange_quantity(self):
        if self.bag_capacity_id:
            return self._onchange_number_of_bags()
        return super(PurchaseOrderLine, self)._onchange_quantity()
