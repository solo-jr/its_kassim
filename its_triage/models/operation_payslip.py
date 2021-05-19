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
from datetime import date, datetime, time
from datetime import timedelta

import babel
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, _, tools
from odoo.exceptions import ValidationError

TICKETS = [20000, 10000, 5000, 2000, 1000]
MAPPING = {
    20000: 'twenty_k_ticket',
    10000: 'ten_k_ticket',
    5000: 'five_k_ticket',
    2000: 'two_k_ticket',
    1000: 'one_k_ticket',
}


class OperationPayslip(models.Model):
    _name = 'operation.payslip'
    _description = 'Pay Slip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Payslip Name', readonly=True,
                       states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id.id)
    number = fields.Char(string='Reference', readonly=True, copy=False,
                         states={'draft': [('readonly', False)]})
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, readonly=True,
                                  states={'draft': [('readonly', False)]})
    date_from = fields.Date(string='Date From', readonly=True, required=True,
                            default=lambda self: fields.Date.to_string(date.today().replace(day=1)),
                            states={'draft': [('readonly', False)]})
    date_to = fields.Date(string='Date To', readonly=True, required=True,
                          default=lambda self: fields.Date.to_string(
                              (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()),
                          states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
    ], string='State', index=True, readonly=True, copy=False, default='draft',
        help="""* When the payslip is created the status is \'Draft\'
                \n* If the payslip is under verification, the status is \'Waiting\'.
                \n* If the payslip is confirmed then status is set to \'Done\'.
                \n* When user cancel payslip the status is \'Rejected\'.""")
    line_ids = fields.One2many('operation.payslip.line', 'slip_id', string='Payslip Lines', readonly=True,
                               states={'draft': [('readonly', False)]})
    company_id = fields.Many2one('res.company', string='Company', readonly=True, copy=False,
                                 default=lambda self: self.env.company,
                                 states={'draft': [('readonly', False)]})
    contract_id = fields.Many2one('hr.contract', string='Contract', readonly=True,
                                  states={'draft': [('readonly', False)]})
    credit_note = fields.Boolean(string='Credit Note', readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 help="Indicates this payslip has a refund of another")
    payslip_run_id = fields.Many2one('operation.payslip.run', string='Payslip Batches', readonly=True,
                                     copy=False, states={'draft': [('readonly', False)]})
    subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal')
    wage = fields.Monetary(related='contract_id.wage', string='Wage', help="Employee's weekly gross wage.")
    amount_total = fields.Monetary(string='Amount total', help="Employee's weekly gross wage.", group_operator='sum',
                                   compute='_compute_subtotal', store=True)
    twenty_k_ticket = fields.Integer(string='20k Ticket', group_operator='sum')
    ten_k_ticket = fields.Integer(string='10k Ticket', group_operator='sum')
    five_k_ticket = fields.Integer(string='5k Ticket', group_operator='sum')
    two_k_ticket = fields.Integer(string='2k Ticket', group_operator='sum')
    one_k_ticket = fields.Integer(string='1k Ticket', group_operator='sum')

    @api.depends('employee_id', 'line_ids')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = sum(rec.line_ids.mapped('total'))
            # rec.amount_total = rec.wage + rec.subtotal
            rec.amount_total = rec.subtotal
            remaining = rec.amount_total
            for ticket in TICKETS:
                # Get number of tickets
                nb = remaining // ticket
                if nb > 0:
                    # Get amount remaining
                    remaining = remaining % ticket
                    rec.write({MAPPING[ticket]: nb})

    def compute_sheet(self):
        for rec in self:
            number = rec.number or self.env['ir.sequence'].next_by_code('salary.slip')
            # Delete old payslip lines
            rec.line_ids.unlink()
            line_ids = [(0, 0, line) for line in self._get_payslip_lines(rec)]
            rec.write({'line_ids': line_ids, 'number': number})
        return True

    @api.model
    def _get_payslip_lines(self, payslip_id):
        triage_obj = self.env['operation.triage']
        wage_by_unit = float(self.env['ir.config_parameter'].sudo().get_param('its_triage.wage_per_unit'))
        date_from = payslip_id.date_from
        # Stop by default date end to 23:59:59
        date_to = fields.Datetime.from_string(payslip_id.date_to) + timedelta(days=1, seconds=-1)
        # Retrieve all triages from the selected period
        triage_ids = triage_obj.search(
            [('type', '=', 'manual'), ('employee_id', '=', payslip_id.employee_id.id)]).filtered(
            lambda x: x.state != 'draft' and x.entry_date and (fields.Datetime.from_string(
                date_from
            ) <= x.output_date <= date_to or fields.Datetime.from_string(
                date_from
            ) <= x.entry_date <= date_to)
        )
        res = []
        for triage_id in triage_ids:
            res += [{'display_type': 'line_section',
                     'name': _('%s / Output Date : %s - Entry Date : %s') % (
                         triage_id.product_id.display_name,
                         fields.Datetime.from_string(triage_id.output_date),
                         fields.Datetime.from_string(triage_id.entry_date))}]
            res += [{'product_id': x.triage_id.product_id.id,
                     'date_from': x.triage_id.output_date,
                     'date_to': x.triage_id.entry_date,
                     'product_template_attribute_value_ids': x.mapped(
                         'product_template_attribute_value_ids.product_attribute_value_id').ids,
                     'amount': wage_by_unit,
                     'quantity': x.quantity}
                    for x in triage_id.mapped('line_ids')]
            # Missing product
            missing_qty = triage_id.output_quantity - sum(triage_id.mapped('line_ids.quantity'))
            if missing_qty > 0:
                res += [{'product_id': triage_id.product_id.id,
                         'date_from': triage_id.output_date,
                         'date_to': triage_id.entry_date,
                         'product_template_attribute_value_ids': self.env['product.attribute.value'].sudo().search(
                             [('name', 'ilike', _('Missing')),
                              ('attribute_id', 'in', triage_id.mapped('attribute_line_ids.attribute_id').ids)]).ids,
                         'amount': wage_by_unit,
                         'quantity': missing_qty}]
        return res

    @api.model
    def get_contract(self, employee, date_from, date_to):
        """
        @param employee: recordset of employee
        @param date_from: date field
        @param date_to: date field
        @return: returns the ids of all the contracts for the given employee that need to be considered for the given dates
        """
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', employee.id), ('state', '=', 'open'), '|',
                        '|'] + clause_1 + clause_2 + clause_3
        return self.env['hr.contract'].search(clause_final).ids

    def onchange_employee_id(self, date_from, date_to, employee_id=False, contract_id=False):
        # defaults
        res = {
            'value': {
                'name': '',
                'contract_id': False,
            }
        }
        if (not employee_id) or (not date_from) or (not date_to):
            return res
        ttyme_from = datetime.combine(fields.Date.from_string(date_from), time.min)
        ttyme_to = datetime.combine(fields.Date.from_string(date_to), time.min)
        employee = self.env['hr.employee'].browse(employee_id)
        locale = self.env.context.get('lang') or 'en_US'
        res['value'].update({
            'name': _('Salary Slip of %s for %s to %s') % (
                employee.name, tools.ustr(babel.dates.format_date(date=ttyme_from, format='dd', locale=locale)),
                tools.ustr(babel.dates.format_date(date=ttyme_to, format='dd-MMMM', locale=locale))),
            'company_id': employee.company_id.id,
        })

        if not self.env.context.get('contract'):
            # fill with the first contract of the employee
            contract_ids = self.get_contract(employee, date_from, date_to)
        else:
            if contract_id:
                # set the list of contract for which the input have to be filled
                contract_ids = [contract_id]
            else:
                # if we don't give the contract, then the input to fill should be for all current contracts of the employee
                contract_ids = self.get_contract(employee, date_from, date_to)

        if not contract_ids:
            return res
        contract = self.env['hr.contract'].browse(contract_ids[0])
        res['value'].update({
            'contract_id': contract.id
        })
        return res

    def set_to_draft(self):
        """
        Set state to 'draft'
        :return:
        """
        for rec in self:
            rec.state = 'draft'

    def set_to_done(self):
        """
        Set state to 'done'
        :return:
        """
        for rec in self:
            rec.compute_sheet()
            rec.state = 'done'

    def set_to_cancel(self):
        """
        Set state to 'rejected'
        :return:
        """
        for rec in self:
            rec.state = 'cancel'


class OperationPayslipLine(models.Model):
    _name = 'operation.payslip.line'
    _description = 'Payslip Line'

    name = fields.Char(string='Product')
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ], default=False, help="Technical field for UX purpose.")
    slip_id = fields.Many2one('operation.payslip', string='Pay Slip', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one('product.product', string='Product')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id.id)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    product_template_attribute_value_ids = fields.Many2many('product.attribute.value',
                                                            string="Attribute Values")
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    amount = fields.Float()
    quantity = fields.Float(default=1.0)
    total = fields.Monetary(string='Total', compute='_compute_total')

    @api.depends('quantity', 'amount')
    def _compute_total(self):
        for rec in self:
            rec.total = float(rec.quantity) * rec.amount

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if 'employee_id' not in values:
                payslip = self.env['operation.payslip'].browse(values.get('slip_id'))
                values['employee_id'] = values.get('employee_id') or payslip.employee_id.id
        return super(OperationPayslipLine, self).create(vals_list)


class OperationPayslipRun(models.Model):
    _name = 'operation.payslip.run'
    _description = 'Payslip Batches'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, readonly=True, states={'draft': [('readonly', False)]})
    slip_ids = fields.One2many('operation.payslip', 'payslip_run_id', string='Payslips', readonly=True,
                               states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('closed', 'Closed'),
    ], string='State', index=True, readonly=True, copy=False, default='draft')
    date_start = fields.Date(string='Date From', required=True, readonly=True,
                             states={'draft': [('readonly', False)]},
                             default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_end = fields.Date(string='Date To', required=True, readonly=True,
                           states={'draft': [('readonly', False)]},
                           default=lambda self: fields.Date.to_string(
                               (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    credit_note = fields.Boolean(string='Credit Note', readonly=True,
                                 states={'draft': [('readonly', False)]},
                                 help="If its checked, indicates that all payslips generated from here are refund payslips.")
    payslip_count = fields.Integer(compute='_compute_payslip_count', string="Payslip Computation Details")

    def set_to_draft(self):
        """
        Set state to 'draft'
        :return:
        """
        for rec in self:
            rec.state = 'draft'

    def set_to_closed(self):
        """
        Set state to 'closed'
        :return:
        """
        for rec in self:
            rec.state = 'closed'

    def set_to_done(self):
        """
        Set state to 'done'
        :return:
        """
        for line in self.slip_ids:
            line.set_to_done()
        for rec in self:
            rec.state = 'done'

    def unlink(self):
        for rec in self:
            if rec.state == 'done':
                raise ValidationError(_('You Cannot Delete Done Payslips Batches'))
        return super(OperationPayslipRun, self).unlink()

    def compute_sheet(self):
        employee_obj = self.env['hr.employee']
        triage_obj = self.env['operation.triage']
        payslip_obj = self.env['operation.payslip']
        from_date = self.date_start
        # Stop by default date end to 23:59:59
        to_date = fields.Datetime.from_string(self.date_end) + timedelta(days=1, seconds=-1)
        # Retrieve all triages from the selected period

        triage_ids = triage_obj.search([('type', '=', 'manual')]).filtered(
            lambda x:  x.state != 'draft' and x.entry_date and (fields.Datetime.from_string(
                from_date
            ) <= x.output_date <= to_date or fields.Datetime.from_string(
                from_date
            ) <= x.entry_date <= to_date)
        )
        for employee in employee_obj.search([('id', 'in', triage_ids.mapped('employee_id').ids)]):
            slip_data = payslip_obj.onchange_employee_id(from_date, to_date, employee.id, contract_id=False)
            res = {
                'employee_id': employee.id,
                'name': slip_data['value'].get('name'),
                'contract_id': slip_data['value'].get('contract_id'),
                'payslip_run_id': self.id,
                'date_from': from_date,
                'date_to': to_date,
                'credit_note': self.credit_note,
                'company_id': employee.company_id.id,
            }
            payslip_obj += self.env['operation.payslip'].create(res)
        payslip_obj.compute_sheet()

    def _compute_payslip_count(self):
        for rec in self:
            rec.payslip_count = len(rec.slip_ids)

    def action_open_payslip(self):
        """
        Open payslip view
        :rtype: object
        """
        action = self.env.ref('its_triage.operation_payslip_menu_action').read()[0]
        action['domain'] = [('payslip_run_id', '=', self.id)]
        return action
