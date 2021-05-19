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
from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from odoo import fields, models


class SaleXlsxReport(models.TransientModel):
    _name = "sale.xlsx.report"

    date_start = fields.Date(string='Date From', required=True,
                             default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_end = fields.Date(string='Date To', required=True,
                           default=lambda self: fields.Date.to_string(
                               (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))

    def action_export(self):
        order_ids = self.env['sale.order'].sudo().search(
            [('date_order', '>=', self.date_start), ('date_order', '<=', self.date_end), ('state', '=', 'sale')],
            order='date_order')

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_sale_xlsx_report?ids=%s' % order_ids.ids
        }
