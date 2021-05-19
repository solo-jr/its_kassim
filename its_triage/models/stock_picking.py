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

from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if self.group_id.sale_id.mapped('order_line.bag_capacity_id'):
            for line in self.group_id.sale_id.mapped('order_line'):
                package_id = self.env['operation.packaging'].sudo().search([('product_id', '=', line.product_id.id)])
                if package_id:
                    current_line = package_id.line_ids.filtered(
                        lambda x: x.bag_capacity_id.id == line.bag_capacity_id.id)
                    current_line.quantity -= line.number_of_bags
        return res
