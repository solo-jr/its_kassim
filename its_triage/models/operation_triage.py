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
import itertools

from odoo import fields, models, api, _, tools
from odoo.exceptions import ValidationError, UserError


class OperationTriage(models.Model):
    _name = "operation.triage"
    _description = "Triage"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Number', required=True, copy=False, default='/')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id.id)
    date = fields.Datetime(string='Date', default=lambda self: fields.Datetime.now())
    output_date = fields.Datetime(string='Output Date', default=lambda self: fields.Datetime.now())
    entry_date = fields.Datetime(string='Entry Date')
    type = fields.Selection([('auto', 'Auto'), ('manual', 'Manual'), ('small', 'Small')])
    product_id = fields.Many2one('product.product', string='Product')
    product_ids = fields.Many2many('product.product', string='Products')
    product_list_ids = fields.One2many('triage.product', 'triage_id', string='Products')
    uom_id = fields.Many2one(related='product_id.uom_id')
    uom_name = fields.Char(string='Unit of Measure Name', related='uom_id.name', readonly=True)
    qty_available = fields.Float(string='Quantity On Hand', digits='Product Unit of Measure', tracking=True,
                                 compute='_compute_qty_available')
    numbers_of_all_round_bags = fields.Float("Numbers of all-round bags")

    attribute_line_ids = fields.One2many('triage.attribute.line', 'triage_id', 'Product Attributes',
                                         copy=True)
    line_ids = fields.One2many('triage.line', 'triage_id', string='Lines')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sorted', 'Sorted'),
        ('cancelled', 'Cancelled')], default='draft',
        copy=False, tracking=True)

    employee_id = fields.Many2one('hr.employee', string='Employee')
    output_quantity = fields.Float("Output Quantity", digits='Product Unit of Measure')
    wage = fields.Monetary(string='Wage', help="Employee's weekly gross wage.", compute='_compute_wage')

    @api.depends('type', 'product_id', 'product_list_ids')
    def _compute_qty_available(self):
        for rec in self:
            if rec.type == 'manual':
                rec.qty_available = rec.product_id.qty_available
            else:
                rec.qty_available = sum(
                    self.env['product.product'].search(
                        [('id', 'in', rec.mapped('product_list_ids.product_id').ids)]).mapped(
                        'qty_available'))

    @api.depends('employee_id', 'line_ids')
    def _compute_wage(self):
        for rec in self:
            wage_par_unit = float(self.env['ir.config_parameter'].sudo().get_param('its_triage.wage_per_unit'))
            # rec.wage = wage_par_unit * sum(rec.line_ids.mapped('quantity')) if rec.line_ids else 0
            rec.wage = wage_par_unit * rec.output_quantity if rec.output_quantity else 0

    def action_sort(self):
        """
        Set state to "sorted" and create automatically variants for the current selected product
        :rtype: object
        """
        for rec in self:
            line_qty = sum(rec.line_ids.mapped('quantity'))
            if rec.type == 'manual' and not rec.entry_date:
                raise UserError(_("Entry date is required. Please fill it."))
            if rec.type == 'manual':
                product_ids = rec.product_id
                available_qty = rec.product_id.qty_available
            else:
                product_ids = rec.product_ids
                available_qty = sum(rec.product_ids.mapped('qty_available'))
            if rec.output_quantity < line_qty:
                raise UserError(_(
                    "This operation is not allowed, the sum of the quantities produced is greater than the sum of the quantities introduced."))
            elif 0 < available_qty < line_qty:
                raise UserError(_("This operation is not allowed, you do not have enough quantity in stock."))

            # product_list_ids = self.product_list_ids
            if rec.type == 'manual' and not self.product_list_ids and rec.product_id and rec.product_id.qty_available:
                rec.write({'product_list_ids':
                               [(0, 0, {
                                   'product_id': rec.product_id.id,
                                   'qty_available': rec.product_id.qty_available,
                                   'output_quantity': rec.output_quantity
                               })]
                           })
            missing_qty = 0
            for list_id in self.product_list_ids:
                attribute_line_ids = list_id.product_id.attribute_line_ids
                # Set state to 'sorted'
                rec.state = 'sorted'
                # Sorting product by variants
                for line in rec.attribute_line_ids:
                    if line.attribute_id.id in attribute_line_ids.mapped('attribute_id').ids:
                        current_line = attribute_line_ids.filtered(lambda x: x.attribute_id.id == line.attribute_id.id)
                        if line.value_ids.ids > current_line.value_ids.ids:
                            res = line.value_ids - current_line.value_ids
                        else:
                            res = current_line.value_ids - line.value_ids
                        missing_id = self.env['product.attribute.value'].sudo().search(
                            [('name', 'ilike', _('Missing')), ('attribute_id', '=', line.attribute_id.id)])
                        current_line.value_ids = [(4, id) for id in res.ids + [missing_id.id]]
                    else:
                        list_id.product_id.product_tmpl_id.attribute_line_ids = [
                            (0, 0, {'attribute_id': line.attribute_id.id,
                                    'value_ids': [
                                        (6, 0, line.value_ids.ids)]})]
                # Update the product source quantity
                if available_qty > 0:
                    self.env['stock.quant']._update_available_quantity(list_id.product_id,
                                                                       self.env.ref('stock.stock_location_stock'),
                                                                       -list_id.output_quantity)
            if rec.type == 'manual' and rec.numbers_of_all_round_bags > 0:
                all_round_bags = self.env['product.template'].search([('is_an_all_round_bag', '=', True)])
                if all_round_bags:
                    if all_round_bags[0].qty_available < rec.numbers_of_all_round_bags:
                        raise UserError(_('not enough bag, there are only %s bags') % all_round_bags[0].qty_available)
                    self.env['stock.quant']._update_available_quantity(all_round_bags[0].product_variant_ids[0],
                                                                       self.env.ref('stock.stock_location_stock'),
                                                                       -rec.numbers_of_all_round_bags)
            # Update the product quantity per variant
            for value in rec.line_ids:
                product_variant_ids = product_ids.mapped('product_variant_ids')
                product_variant_id = product_variant_ids.filtered(
                    lambda x: x.product_template_attribute_value_ids.mapped(
                        'name') == value.product_template_attribute_value_ids.mapped('name'))
                self.env['stock.quant']._update_available_quantity(product_variant_id,
                                                                   self.env.ref('stock.stock_location_stock'),
                                                                   value.quantity)
            # Update "missing" product quantity variant
            missing_qty = sum(self.product_list_ids.mapped('output_quantity')) - sum(self.line_ids.mapped('quantity'))
            product_variant_id = product_ids.mapped('product_variant_ids').filtered(
                lambda x: x.product_template_attribute_value_ids.mapped('name')[0] == _('Missing'))
            if product_variant_id:
                self.env['stock.quant']._update_available_quantity(product_variant_id,
                                                                   self.env.ref('stock.stock_location_stock'),
                                                                   missing_qty)

    def action_cancel(self):
        """
        Set state to "concelled"
        :rtype: object
        """
        for rec in self:
            rec.state = 'cancelled'

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('triage')
        res = super(OperationTriage, self).create(values)
        if 'attribute_line_ids' in values:
            res._create_attribute_value(values)
        if 'product_list_ids' in values:
            res.product_ids = res.mapped('product_list_ids.product_id').ids
            res.output_quantity = sum(res.mapped('product_list_ids.output_quantity'))
        return res

    def write(self, values):
        res = super(OperationTriage, self).write(values)
        if 'attribute_line_ids' in values:
            self._create_attribute_value(values)
        if 'product_list_ids' in values:
            self.product_ids = self.mapped('product_list_ids.product_id').ids
            self.output_quantity = sum(self.mapped('product_list_ids.output_quantity'))
        return res

    def _create_attribute_value(self, values):
        if 'attribute_line_ids' in values:
            # Create combination
            all_combinations = itertools.product(
                *[ptal.product_template_value_ids.filtered(lambda ptav: ptav.ptav_active) for ptal in
                  self.attribute_line_ids])
            line_ids = []
            # For each possible variant, create if it doesn't exist yet.
            for combination_tuple in all_combinations:
                combination = self.env['triage.attribute.value'].concat(*combination_tuple)
                if combination:
                    line_ids.append([0, 0, {
                        'product_template_attribute_value_ids': [(6, 0, combination.ids)],
                        'quantity': 0,
                    }])
            self.line_ids = [(6, 0, [])] + line_ids

            # Create attribute "Missing"
            attribute_obj = self.env['product.attribute.value']
            attribute_id = values['attribute_line_ids'][0][2]['attribute_id'] or False
            missing_id = attribute_obj.sudo().search(
                [('name', 'ilike', _('Missing')), ('attribute_id', '=', attribute_id)])
            if not missing_id:
                attribute_obj.create({
                    'name': _('Missing'),
                    'attribute_id': attribute_id,
                })


class TriageAttributeLine(models.Model):
    """Attributes available on operation.triage with their selected values in a m2m.
    Used as a configuration model to generate the appropriate triage.attribute.value"""

    _name = "triage.attribute.line"
    _rec_name = 'attribute_id'
    _description = 'Triage Attribute Line'
    _order = 'attribute_id, id'

    active = fields.Boolean(default=True)
    triage_id = fields.Many2one('operation.triage', string='Triage', index=True)
    attribute_id = fields.Many2one('product.attribute', string="Attribute", index=True)
    value_ids = fields.Many2many('product.attribute.value', string="Values",
                                 domain="[('attribute_id', '=', attribute_id)]",
                                 relation='product_attribute_value_triage_attribute_line_rel')
    product_template_value_ids = fields.One2many('triage.attribute.value', 'attribute_line_id',
                                                 string="Triage Attribute Values")

    @api.onchange('attribute_id')
    def _onchange_attribute_id(self):
        self.value_ids = self.value_ids.filtered(lambda pav: pav.attribute_id == self.attribute_id)

    @api.constrains('active', 'value_ids', 'attribute_id')
    def _check_valid_values(self):
        for ptal in self:
            if ptal.active and not ptal.value_ids:
                if ptal.triage_id.type == 'manual':
                    raise ValidationError(
                        _("The attribute %s must have at least one value for the product %s.") %
                        (ptal.attribute_id.display_name, ptal.triage_id.product_id.display_name)
                    )
                else:
                    raise ValidationError(
                        _("The attribute %s must have at least one value for the products %s.") %
                        (ptal.attribute_id.display_name, ','.join(ptal.triage_id.product_ids.mapped('display_name')))
                    )
            for pav in ptal.value_ids:
                if pav.attribute_id != ptal.attribute_id:
                    raise ValidationError(
                        _(
                            "On the product %s you cannot associate the value %s with the attribute %s because they do not match.") %
                        (ptal.product_tmpl_id.display_name, pav.display_name, ptal.attribute_id.display_name)
                    )
        return True

    @api.model_create_multi
    def create(self, vals_list):
        """Override to:
        - Activate archived lines having the same configuration (if they exist)
            instead of creating new lines.
        - Set up related values and related variants.

        Reactivating existing lines allows to re-use existing variants when
        possible, keeping their configuration and avoiding duplication.
        """
        create_values = []
        activated_lines = self.env['triage.attribute.line']
        for value in vals_list:
            vals = dict(value, active=value.get('active', True))
            # While not ideal for peformance, this search has to be done at each
            # step to exclude the lines that might have been activated at a
            # previous step. Since `vals_list` will likely be a small list in
            # all use cases, this is an acceptable trade-off.
            archived_ptal = self.search([
                ('active', '=', False),
                ('triage_id', '=', vals.pop('triage_id', 0)),
                ('attribute_id', '=', vals.pop('attribute_id', 0)),
            ], limit=1)
            if archived_ptal:
                # Write given `vals` in addition of `active` to ensure
                # `value_ids` or other fields passed to `create` are saved too,
                # but change the context to avoid updating the values and the
                # variants until all the expected lines are created/updated.
                archived_ptal.with_context(update_triage_attribute_values=False).write(vals)
                activated_lines += archived_ptal
            else:
                create_values.append(value)
        res = activated_lines + super(TriageAttributeLine, self).create(create_values)
        res._update_triage_attribute_values()
        return res

    def write(self, values):
        res = super(TriageAttributeLine, self).write(values)
        # If coming from `create`, no need to update the values and the variants
        # before all lines are created.
        if self.env.context.get('update_triage_attribute_values', True):
            self._update_triage_attribute_values()
        return res

    def _update_triage_attribute_values(self):
        """Create or unlink `product.template.attribute.value` for each line in
        `self` based on `value_ids`.

        The goal is to delete all values that are not in `value_ids`, to
        activate those in `value_ids` that are currently archived, and to create
        those in `value_ids` that didn't exist.

        This is a trick for the form view and for performance in general,
        because we don't want to generate in advance all possible values for all
        templates, but only those that will be selected.
        """
        TriageAttributeValue = self.env['triage.attribute.value']
        ptav_to_create = []
        ptav_to_unlink = TriageAttributeValue
        for ptal in self:
            ptav_to_activate = TriageAttributeValue
            remaining_pav = ptal.value_ids
            for ptav in ptal.product_template_value_ids:
                if ptav.product_attribute_value_id not in remaining_pav:
                    # Remove values that existed but don't exist anymore, but
                    # ignore those that are already archived because if they are
                    # archived it means they could not be deleted previously.
                    if ptav.ptav_active:
                        ptav_to_unlink += ptav
                else:
                    # Activate corresponding values that are currently archived.
                    remaining_pav -= ptav.product_attribute_value_id
                    if not ptav.ptav_active:
                        ptav_to_activate += ptav

            for pav in remaining_pav:
                # The previous loop searched for archived values that belonged to
                # the current line, but if the line was deleted and another line
                # was recreated for the same attribute, we need to expand the
                # search to those with matching `attribute_id`.
                # While not ideal for peformance, this search has to be done at
                # each step to exclude the values that might have been activated
                # at a previous step. Since `remaining_pav` will likely be a
                # small list in all use cases, this is an acceptable trade-off.
                ptav = TriageAttributeValue.search([
                    ('ptav_active', '=', False),
                    ('triage_id', '=', ptal.triage_id.id),
                    ('attribute_id', '=', ptal.attribute_id.id),
                    ('product_attribute_value_id', '=', pav.id),
                ], limit=1)
                if ptav:
                    ptav.write({'ptav_active': True, 'attribute_line_id': ptal.id})
                    # If the value was marked for deletion, now keep it.
                    ptav_to_unlink -= ptav
                else:
                    # create values that didn't exist yet
                    ptav_to_create.append({
                        'product_attribute_value_id': pav.id,
                        'attribute_line_id': ptal.id,
                        'triage_id': ptal.triage_id.id
                    })
            # Handle active at each step in case a following line might want to
            # re-use a value that was archived at a previous step.
            ptav_to_activate.write({'ptav_active': True})
            ptav_to_unlink.write({'ptav_active': False})
        ptav_to_unlink.unlink()
        TriageAttributeValue.create(ptav_to_create)

    def unlink(self):
        """Override to:
        - Archive the line if unlink is not possible.
        - Clean up related values and related variants.

        Archiving is typically needed when the line has values that can't be
        deleted because they are referenced elsewhere (on a variant that can't
        be deleted, on a sales order line, ...).
        """
        # Now delete or archive the lines.
        ptal_to_archive = self.env['triage.attribute.line']
        for ptal in self:
            try:
                with self.env.cr.savepoint(), tools.mute_logger('odoo.sql_db'):
                    super(TriageAttributeLine, ptal).unlink()
            except Exception:
                # We catch all kind of exceptions to be sure that the operation
                # doesn't fail.
                ptal_to_archive += ptal
        ptal_to_archive.write({'active': False})
        return True


class TriageAttributeValue(models.Model):
    """Materialized relationship between attribute values
    and product template generated by the triage.attribute.line"""

    _name = "triage.attribute.value"
    _description = "Triage Attribute Value"
    _order = 'attribute_line_id, product_attribute_value_id, id'

    # Not just `active` because we always want to show the values except in
    # specific case, as opposed to `active_test`.
    ptav_active = fields.Boolean("Active", default=True)
    name = fields.Char('Value', related="product_attribute_value_id.name")
    triage_id = fields.Many2one('operation.triage', string='Triage')

    # defining fields: the product template attribute line and the product attribute value
    product_attribute_value_id = fields.Many2one(
        'product.attribute.value', string='Attribute Value', index=True)
    attribute_line_id = fields.Many2one('triage.attribute.line', required=True, ondelete='cascade', index=True)

    # related fields: product template and product attribute
    attribute_id = fields.Many2one('product.attribute', string="Attribute", related='attribute_line_id.attribute_id',
                                   store=True, index=True)
    ptav_product_variant_ids = fields.Many2many('product.product', relation='product_variant_combination',
                                                string="Related Variants", readonly=True)

    _sql_constraints = [
        ('attribute_value_unique', 'unique(attribute_line_id, product_attribute_value_id)',
         "Each value should be defined only once per attribute per product."),
    ]

    @api.constrains('attribute_line_id', 'product_attribute_value_id')
    def _check_valid_values(self):
        for ptav in self:
            if ptav.product_attribute_value_id not in ptav.attribute_line_id.value_ids:
                raise ValidationError(
                    _("The value %s is not defined for the attribute %s on the product %s.") %
                    (ptav.product_attribute_value_id.display_name, ptav.attribute_id.display_name,
                     ptav.product_tmpl_id.display_name)
                )

    def name_get(self):
        """Override because in general the name of the value is confusing if it
        is displayed without the name of the corresponding attribute.
        Eg. on exclusion rules form
        """
        return [(value.id, "%s: %s" % (value.attribute_id.name, value.name)) for value in self]

    def unlink(self):
        """Override to:
        - Clean up the variants that use any of the values in self:
            - Remove the value from the variant if the value belonged to an
                attribute line with only one value.
            - Unlink or archive all related variants.
        - Archive the value if unlink is not possible.

        Archiving is typically needed when the value is referenced elsewhere
        (on a variant that can't be deleted, on a sales order line, ...).
        """
        # Directly remove the values from the variants for lines that had single
        # value (counting also the values that are archived).
        single_values = self.filtered(lambda ptav: len(ptav.attribute_line_id.product_template_value_ids) == 1)
        for ptav in single_values:
            ptav.ptav_product_variant_ids.write({'product_template_attribute_value_ids': [(3, ptav.id, 0)]})
        # Now delete or archive the values.
        ptav_to_archive = self.env['triage.attribute.value']
        for ptav in self:
            try:
                with self.env.cr.savepoint(), tools.mute_logger('odoo.sql_db'):
                    super(TriageAttributeValue, ptav).unlink()
            except Exception:
                # We catch all kind of exceptions to be sure that the operation
                # doesn't fail.
                ptav_to_archive += ptav
        ptav_to_archive.write({'ptav_active': False})
        return True


class TriageProduct(models.Model):
    _name = "triage.product"
    _description = "Triage Product"

    triage_id = fields.Many2one('operation.triage', string='Triage', index=True)
    product_id = fields.Many2one('product.product', string='Product')
    qty_available = fields.Float(string='Quantity On Hand', digits='Product Unit of Measure')
    output_quantity = fields.Float("Output Quantity", digits='Product Unit of Measure')

    @api.onchange('product_id')
    def onchange_product_id(self):
        for rec in self:
            if rec.product_id:
                rec.qty_available = sum(
                    self.env['product.product'].search([('id', '=', rec.product_id.id)]).mapped('qty_available'))

    @api.onchange('output_quantity')
    def onchange_output_quantity(self):
        for rec in self:
            if rec.output_quantity > rec.qty_available:
                raise UserError(_("This operation is not allowed, you do not have enough quantity in stock."))


class TriageLine(models.Model):
    _name = "triage.line"
    _description = "Triage Line"

    triage_id = fields.Many2one('operation.triage', string='Triage', index=True)
    product_template_attribute_value_ids = fields.Many2many('triage.attribute.value',
                                                            string="Attribute Values")
    quantity = fields.Float("Quantity", digits='Product Unit of Measure', required=True)


class OperationCapacity(models.Model):
    _name = "operation.capacity"
    _description = "Bag Capacity"

    active = fields.Boolean('Active', default=True)
    name = fields.Char(string='Name', required=True, copy=False, default='/')
    capacity = fields.Float("Capacity", digits='Product Unit of Measure', required=True)
