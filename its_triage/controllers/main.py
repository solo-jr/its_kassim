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
from datetime import datetime
from io import BytesIO

import xlsxwriter

from odoo import http, _
from odoo.addons.web.controllers.main import content_disposition
from odoo.http import request


class PurchaseXlsxBinary(http.Controller):

    def convert(self, currency):
        """
        Add currency symbol
        :param currency: currency
        :return:
        """
        if currency.position == 'before':
            return u'{symbol}\N{NO-BREAK SPACE}#,##0.00'.format(symbol=currency.symbol or '')
        else:
            return u'#,##0.00\N{NO-BREAK SPACE}{symbol}'.format(symbol=currency.symbol or '')

    @http.route('/web/binary/download_purchase_xlsx_report', type='http', auth="public")
    def download_purchase_xlsx_report(self, ids, **kwargs):
        """
        Export selected purchase orders to .xlsx format
        :param ids:
        :param kwargs:
        :return:
        """
        purchase_ids = request.env['purchase.order'].sudo().browse(eval(ids))
        order_header = [_('Date'), _('Number of Bags'), _('Total weight in kg'), _('Quality'), _('Price of Kg'),
                        _('Price Total'), _('Supplier'), _('Truck Number'), _('Order Number'), _('Total Docker Cost'),
                        _('Total Cost')]
        header = [_('Number of Bags'), _('Total weight in kg'), _('Price Total'), _('Total Docker Cost'),
                  _('Total Cost')]
        summary_header = [_('Supplier'), _('Number of Bags'), _('Total weight in kg'), _('Price Total')]
        file = BytesIO()
        filename = _("Orders - %s.xlsx") % (datetime.today().strftime('%d_%m_%Y_%H_%M_%S'))
        workbook = xlsxwriter.Workbook(file)

        # Define workbook stylesheet
        head_style = workbook.add_format(
            {'font_size': 11, 'font_name': 'Calibri', 'border': 1, 'bold': True, 'align': 'left', 'valign': 'vcenter',
             'text_wrap': 1})
        text_format = workbook.add_format({'font_size': 11, 'font_name': 'Calibri', 'border': 1, 'align': 'left'})
        number_format = workbook.add_format(
            {'num_format': '#,##0.00', 'font_size': 11, 'font_name': 'Calibri', 'border': 1})
        date_format = workbook.add_format(
            {'num_format': 'dd/mm/yyyy', 'font_size': 11, 'font_name': 'Calibri', 'border': 1})
        monetary_format = workbook.add_format(
            {'num_format': self.convert(request.env.user.company_id.currency_id), 'font_size': 11,
             'font_name': 'Calibri', 'border': 1})
        title_style_1 = workbook.add_format(
            {'font_size': 12, 'bold': True, 'font_name': 'Calibri', 'align': 'center', 'border': 1})

        # Adding new tab named : 'Purchase Details'
        order_worksheet = workbook.add_worksheet(_("Purchase Details"))
        order_worksheet.merge_range('A%s:K%s' % (1, 1), _('Purchase Details'), title_style_1)

        index = 0
        for title in order_header:
            # Define column size
            order_worksheet.set_column(index, index, 17.5)
            order_worksheet.write(1, index, title, head_style)
            index += 1

        index = 0
        for rec in purchase_ids.mapped('order_line'):
            order_worksheet.write(index + 2, 0, rec.order_id.date_order, date_format)
            order_worksheet.write_number(index + 2, 1, rec.number_of_bags, number_format)
            order_worksheet.write_number(index + 2, 2, rec.product_qty, number_format)
            order_worksheet.write(index + 2, 3, rec.product_id.display_name, text_format)
            order_worksheet.write_number(index + 2, 4, rec.price_unit, monetary_format)
            order_worksheet.write_number(index + 2, 5, rec.price_subtotal, monetary_format)
            order_worksheet.write(index + 2, 6, rec.order_id.partner_id.name, text_format)
            order_worksheet.write(index + 2, 7, rec.order_id.truck_number or '', text_format)
            order_worksheet.write(index + 2, 8, rec.order_id.name, text_format)
            order_worksheet.write_number(index + 2, 9, rec.order_id.docker_fees, monetary_format)
            order_worksheet.write_number(index + 2, 10, rec.order_id.docker_fees, monetary_format)
            index += 1

        # Adding new tab named : 'Orders'
        worksheet = workbook.add_worksheet(_("General Information"))

        worksheet.merge_range('A%s:E%s' % (1, 1), _('Total Purchase'), title_style_1)

        index = 0
        for title in header:
            # Define column size
            worksheet.set_column(index, index, 17.5)
            worksheet.write(1, index, title, head_style)
            index += 1

        worksheet.write_number(2, 0, sum(purchase_ids.mapped('order_line.number_of_bags')), number_format)
        worksheet.write_number(2, 1, sum(purchase_ids.mapped('order_line.product_qty')), number_format)
        worksheet.write_number(2, 2, sum(purchase_ids.mapped('order_line.price_subtotal')), monetary_format)
        worksheet.write_number(2, 3, sum(purchase_ids.mapped('docker_fees')), monetary_format)
        worksheet.write_number(2, 4, sum(purchase_ids.mapped('docker_fees')), monetary_format)

        worksheet.merge_range('A%s:D%s' % (6, 6), _('Purchase Summary'), title_style_1)

        index = 0
        for title in summary_header:
            worksheet.write(6, index, title, head_style)
            index += 1

        index = 0
        for rec in purchase_ids:
            worksheet.write(index + 7, 0, rec.partner_id.name, text_format)
            worksheet.write_number(index + 7, 1, sum(rec.mapped('order_line.number_of_bags')), number_format)
            worksheet.write_number(index + 7, 2, sum(rec.mapped('order_line.product_qty')), number_format)
            worksheet.write_number(index + 7, 3, sum(rec.mapped('order_line.price_subtotal')), monetary_format)
            index += 1

        workbook.close()
        return request.make_response(file.getvalue(), [('Content-Type', 'application/octet-stream'),
                                                       ('Content-Disposition', content_disposition(filename))])

    @http.route('/web/binary/download_sale_xlsx_report', type='http', auth="public")
    def download_sale_xlsx_report(self, ids, **kwargs):
        """
        Export selected sale orders to .xlsx format
        :param ids:
        :param kwargs:
        :return:
        """
        order_ids = request.env['sale.order'].sudo().browse(eval(ids))
        row = [_('Departure costs'), _('Rights and taxes'), _('Transport Delivery'), _('Other Expenses')]
        row_values = {
            0: [
                'sea_freight',
                'boarding_and_scan',
                'purchase_msc_lead',
                'application_fees'
            ],
            1: [
                'pg_gasy_net',
                'docker_stuffing_costs',
                'fimugation_certificate',
                'phytosanitary_certificate',
                'region_rebate',
                'apmf',
                'ccco_commerce_law',
                'certificate_of_origin',
                'honorary_llyods'
            ],
            2: [
                'stuffing_truck',
                'transit',
                'disbursement_costs'
            ],
            3: [
                'label',
                'stuffing',
                'phyto_commission',
                'dhl_shipping',
                'other_expenses'
            ]
        }
        file = BytesIO()
        filename = _("Sales - %s.xlsx") % (datetime.today().strftime('%d_%m_%Y_%H_%M_%S'))
        workbook = xlsxwriter.Workbook(file)

        # Define workbook stylesheet
        text_format = workbook.add_format({'font_size': 11, 'font_name': 'Calibri', 'border': 1, 'align': 'left'})
        number_format = workbook.add_format(
            {'num_format': '#,##0.00', 'font_size': 11, 'font_name': 'Calibri', 'border': 1})
        monetary_format = workbook.add_format(
            {'num_format': self.convert(request.env.user.company_id.currency_id), 'font_size': 11,
             'font_name': 'Calibri', 'border': 1})
        title_style_1 = workbook.add_format(
            {'font_size': 12, 'bold': True, 'font_name': 'Calibri', 'align': 'center', 'border': 1})

        # Adding new tab named : 'Sales'
        worksheet = workbook.add_worksheet(_("Sales"))

        worksheet.write(0, 0, _('Number of container'), title_style_1)
        worksheet.write_number(0, 1, sum(order_ids.mapped('number_of_container')), number_format)
        worksheet.write(1, 0, _('Total number of bags'), title_style_1)
        worksheet.write_number(1, 1, sum(order_ids.mapped('order_line.product_uom_qty')), number_format)

        index = row_number = 0
        for title in row:
            # Define column size
            worksheet.set_column(index, index, 25)
            worksheet.merge_range('A%s:B%s' % (row_number + 4, row_number + 4), title, title_style_1)
            for value in row_values[index]:
                worksheet.write(row_number + 4, 0, request.env['sale.order'].fields_get(value)[value]['string'],
                                text_format)
                worksheet.write_number(row_number + 4, 1, sum(order_ids.mapped(value)), monetary_format)
                row_number += 1
            index += 1
            row_number += 1

        # Add General total at the end of table
        worksheet.write(row_number + 3, 0, _('GENERAL TOTAL'), title_style_1)
        worksheet.write_formula(row_number + 3, 1, '=SUM(B%s:B%s)' % (5, row_number + 1), monetary_format)

        workbook.close()
        return request.make_response(file.getvalue(), [('Content-Type', 'application/octet-stream'),
                                                       ('Content-Disposition', content_disposition(filename))])

    def fill_column(self, **kwargs):
        if kwargs.get('record_id') in kwargs.get('headers'):
            for rec in kwargs.get('headers')[kwargs.get('record_id')]:
                kwargs.get('worksheet').write_number(kwargs.get('index') + 1, rec['position'], rec['value'],
                                                     kwargs.get('format'))
                kwargs.get('worksheet').write_number(kwargs.get('index') + 1, len(kwargs.get('header')) - 1,
                                                     rec['missing_qty'], kwargs.get('format'))

    @http.route('/web/binary/download_triage_xlsx_report', type='http', auth="public")
    def download_triage_xlsx_report(self, ids, type, **kwargs):
        """
        Export selected triages to .xlsx format
        :param ids:
        :param kwargs:
        :return:
        """
        triage_ids = request.env['operation.triage'].sudo().browse(eval(ids))
        if type == 'manual':
            header = [_('Name'), _('Ref.'), _('Output weight'), _('Entry Date')]
        else:
            header = [_('Ref.'), _('Output weight'), _('Entry Date')]
        file = BytesIO()
        filename = _("Triages - %s.xlsx") % (datetime.today().strftime('%d_%m_%Y_%H_%M_%S'))
        workbook = xlsxwriter.Workbook(file)

        # Define workbook stylesheet
        head_style = workbook.add_format(
            {'font_size': 11, 'font_name': 'Calibri', 'border': 1, 'bold': True, 'align': 'left', 'valign': 'vcenter',
             'text_wrap': 1})
        text_format = workbook.add_format({'font_size': 11, 'font_name': 'Calibri', 'border': 1, 'align': 'left'})
        number_format = workbook.add_format(
            {'num_format': '#,##0.00', 'font_size': 11, 'font_name': 'Calibri', 'border': 1})
        date_format = workbook.add_format(
            {'num_format': 'dd/mm/yyyy', 'font_size': 11, 'font_name': 'Calibri', 'border': 1})

        # Adding new tab named : 'Manual'
        if type == 'manual':
            worksheet = workbook.add_worksheet(_("Manual"))
        elif type == 'small':
            worksheet = workbook.add_worksheet(_("Small"))
        else:
            worksheet = workbook.add_worksheet(_("Auto"))

        headers = {}
        line_ids = triage_ids.mapped('line_ids')
        product_ids = triage_ids.mapped('product_id') if type == 'manual' else triage_ids.mapped('product_ids')
        for product_id in product_ids:
            for value in line_ids:
                product_variant_ids = product_id.product_variant_ids
                product_variant_id = product_variant_ids.filtered(
                    lambda x: x.product_template_attribute_value_ids.mapped(
                        'name') == value.product_template_attribute_value_ids.mapped('name'))
                if product_variant_id and product_variant_id.mapped('display_name')[0] not in header:
                    header += product_variant_id.mapped('display_name')
                else:
                    pass
                missing_qty = (value.triage_id.output_quantity - sum(value.triage_id.mapped('line_ids.quantity'))) \
                    if value.triage_id.output_quantity > sum(value.triage_id.mapped('line_ids.quantity')) else 0
                if value.triage_id.id in headers:
                    headers[value.triage_id.id] += [{
                        'value': value.quantity,
                        'missing_qty': missing_qty,
                        'position': header.index(product_variant_id.mapped('display_name')[0])
                    }]
                else:
                    headers.update(
                        {value.triage_id.id:
                            [{
                                'value': value.quantity,
                                'missing_qty': missing_qty,
                                'position': header.index(product_variant_id.mapped('display_name')[0])
                            }]
                        })

        index = 0
        header.append(_('Missing'))
        for title in header:
            # Define column size
            worksheet.set_column(index, index, 17.5)
            worksheet.write(0, index, title, head_style)
            index += 1

        index = 0
        for rec in triage_ids:
            if type == 'manual':
                worksheet.write(index + 1, 0, rec.employee_id.name, text_format)
                worksheet.write(index + 1, 1, rec.name, text_format)
                worksheet.write_number(index + 1, 2, rec.output_quantity, number_format)
                worksheet.write(index + 1, 3, rec.entry_date, date_format)
            else:
                worksheet.write(index + 1, 0, rec.name, text_format)
                worksheet.write_number(index + 1, 1, rec.output_quantity, number_format)
                worksheet.write(index + 1, 2, rec.output_date, date_format)
            # Fill the table with list of variants
            values = {'worksheet': worksheet, 'record_id': rec.id, 'header': header, 'headers': headers, 'index': index,
                      'format': number_format}
            self.fill_column(**values)
            index += 1

        # Set border dynamically for all empty cells
        # With Row/Column notation we specify all four cells in the range:
        # (first_row, first_col, last_row, last_col)
        cell_format = workbook.add_format({'border': 1})
        worksheet.conditional_format(0, 0, index, len(header) - 1, {'type': 'blanks', 'format': cell_format})

        workbook.close()
        return request.make_response(file.getvalue(), [('Content-Type', 'application/octet-stream'),
                                                       ('Content-Disposition', content_disposition(filename))])
