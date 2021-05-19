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


class StockMove(models.Model):
    _inherit = 'stock.move'

    bag_capacity = fields.Char(string='Bag Capacity', compute='_compute_bag_capacity')

    @api.depends('sale_line_id', 'purchase_line_id')
    def _compute_bag_capacity(self):
        for rec in self:
            if rec.sale_line_id and rec.sale_line_id.bag_capacity_id:
                rec.bag_capacity = '%s x %s' % \
                                   (rec.sale_line_id.number_of_bags, rec.sale_line_id.bag_capacity_id.name)
            elif rec.purchase_line_id and rec.purchase_line_id.bag_capacity_id:
                rec.bag_capacity = '%s x %s' % \
                                   (rec.purchase_line_id.number_of_bags, rec.purchase_line_id.bag_capacity_id.name)
            else:
                rec.bag_capacity = False
