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
{
    'name': "Triage",
    'summary': 'Manage Triage',
    'description': """
This module adds feature to manage triage in Odoo
=====================
    """,
    'author': "IT-Solutions.mg",
    'category': 'Inventory',
    'version': '0.1',

    'depends': [
        'sale', 'sale_management', 'stock', 'hr', 'hr_contract', 'purchase', 'account'
    ],

    'data': [
        # data
        'data/ir_sequence_data.xml',
        'data/capacity_data.xml',
        # security
        'security/ir.model.access.csv',
        # reports
        'reports/triage_xls_report_views.xml',
        'reports/purchase_xls_report_views.xml',
        'reports/sale_xls_report_views.xml',
        # views
        'views/operation_triage_views.xml',
        'views/operation_payslip_views.xml',
        'views/operation_capacity_views.xml',
        'views/operation_packaging_views.xml',
        'views/purchase_views.xml',
        'views/account_views.xml',
        'views/order_views.xml',
        'views/stock_picking_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_view.xml',
        # wizards
        'wizard/update_quantity_wizard_views.xml',
    ],
    'demo': [
    ],
    'qweb': [],
    'sequence': -10,
    'installable': True,
    'application': True,
    'license': 'AGPL-3',
}
##############################################################################
