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
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    number_of_container = fields.Integer(string='Number of container')

    # Departure costs
    sea_freight = fields.Monetary(string='Sea freight')
    boarding_and_scan = fields.Monetary(string='Boarding + scan')
    purchase_msc_lead = fields.Monetary(string='Purchase MSC lead')
    application_fees = fields.Monetary(string='Application fees')

    # Rights and taxes
    pg_gasy_net = fields.Monetary(string='PG Gasy net')
    docker_stuffing_costs = fields.Monetary(string='Docker stuffing costs')
    fimugation_certificate = fields.Monetary(string='Fimugation certificate')
    phytosanitary_certificate = fields.Monetary(string='Phytosanitary certificate')
    region_rebate = fields.Monetary(string='Region rebate')
    apmf = fields.Monetary(string='APMF')
    ccco_commerce_law = fields.Monetary(string='CCCO Commerce Law')
    certificate_of_origin = fields.Monetary(string='Certificate of origin right')
    honorary_llyods = fields.Monetary(string='Honorary Llyod\'s')

    # Transport Delivery
    stuffing_truck = fields.Monetary(string='Stuffing truck')
    transit = fields.Monetary(string='Transit')
    disbursement_costs = fields.Monetary(string='Customs disbursement costs')

    # Other Expenses
    label = fields.Monetary(string='Label')
    stuffing = fields.Monetary(string='Stuffing')
    phyto_commission = fields.Monetary(string='Phyto Commission')
    dhl_shipping = fields.Monetary(string='DHL Shipping')
    other_expenses = fields.Monetary(string='Other Expenses')


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    number_of_bags = fields.Integer(string='Number of Bags')
    bag_capacity_id = fields.Many2one('operation.capacity', string='Bag Capacity')

    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        if self.bag_capacity_id:
            return self._check_packaging()
        return super(SaleOrderLine, self).product_uom_change()

    @api.onchange('number_of_bags')
    def _onchange_number_of_bags(self):
        if self.number_of_bags and self.bag_capacity_id:
            self.product_uom_qty = self.number_of_bags * self.bag_capacity_id.capacity

    @api.onchange('bag_capacity_id')
    def _onchange_bag_capacity_id(self):
        if self.bag_capacity_id:
            return self._check_packaging()

    def _check_packaging(self):
        qty = 0
        self._onchange_number_of_bags()
        package_id = self.env['operation.packaging'].sudo().search([('product_id', '=', self.product_id.id)])
        if package_id:
            qty = package_id.line_ids.filtered(lambda x: x.bag_capacity_id.id == self.bag_capacity_id.id).quantity
        if package_id and self.number_of_bags > qty:
            raise UserError(_("This product is packaged for %.2f bag(s) of %s. You try to sell %.2f bag(s).") % (
                qty, self.bag_capacity_id.name, self.product_uom_qty))
        if not self.product_uom or not self.product_id:
            self.price_unit = 0.0
            return
        if self.order_id.pricelist_id and self.order_id.partner_id:
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id,
                quantity=self.product_uom_qty,
                date=self.order_id.date_order,
                pricelist=self.order_id.pricelist_id.id,
                uom=self.product_uom.id,
                fiscal_position=self.env.context.get('fiscal_position')
            )
            self.price_unit = self.env['account.tax']._fix_tax_included_price_company(
                self._get_display_price(product),
                product.taxes_id, self.tax_id,
                self.company_id)
        return {}
