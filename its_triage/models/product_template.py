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


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_an_all_round_bag = fields.Boolean("Is an all-round bag")
    # default values automatic sorting
    is_dv_automatic_sorting = fields.Boolean("Default values for automatic sorting")
    as_product_input_ids = fields.Many2many("product.product", relation="as_product_input_ids_rel",
                                            string="Product input",
                                            domain="[('product_tmpl_id', '=', id)]")
    as_product_output_ids = fields.Many2many("product.product", relation="as_product_output_ids_rel",
                                             string="Product output",
                                             domain="[('product_tmpl_id', '=', id)]")
    # default values manual sorting
    is_dv_manual_sorting = fields.Boolean("Default values for manual sorting")
    ms_product_input_id = fields.Many2one("product.product", string="Product input",
                                          domain="[('product_tmpl_id', '=', id)]")
    ms_product_output_ids = fields.Many2many("product.product", relation="ms_product_output_ids_rel",
                                             string="Product output",
                                             domain="[('product_tmpl_id', '=', id)]")
    # smalls values manual sorting
    is_dv_smalls_sorting = fields.Boolean("Default values for smals sorting")
    ss_product_input_ids = fields.Many2many("product.product", relation="ss_product_input_ids_rel",
                                            string="Product input",
                                            domain="[('product_tmpl_id', '=', id)]")
    ss_product_output_ids = fields.Many2many("product.product", relation="ss_product_output_ids_rel",
                                             string="Product output",
                                             domain="[('product_tmpl_id', '=', id)]")
