from odoo import models, fields, api, _
from datetime import date, datetime, timedelta
from odoo.exceptions import ValidationError

import logging
from lxml import etree
import json

_logger = logging.getLogger(__name__)


class HrLeavePolicyHeader(models.Model):
    _name = "hr.leave.policy.header"
    _description = 'Leave Balance Company Policy'

    @api.model
    def default_get(self, fields):
        res = super(HrLeavePolicyHeader, self).default_get(fields)
        if not res.get('name') and res.get('company_id'):
            res['name'] = _('Time Off Allocation Policy for %s', self.env['res.company'].browse(res['company_id']).name)
        return res

    name = fields.Char(required=True)
    active = fields.Boolean("Active", default=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company)
    matrix_ids = fields.One2many('hr.leave.policy', 'header_id', 'Leave Balance Policy')

    @api.constrains('matrix_ids')
    def _check_grade(self):
        if any(line.to_grade.sequence == line.from_grade.sequence for line in self.matrix_ids) or \
        any(line.to_grade.sequence < line.from_grade.sequence for line in self.matrix_ids):
            raise ValidationError(_("'To Grade' must be greater than 'From Grade'."))

    @api.constrains('active')
    def _constraint_active_policy(self):
        policy = self.search([('company_id', '=', self.company_id.id),('active', '=', True)])
        if len(policy) > 1:
            raise ValidationError(_("Can't set more than one active leave policy in %s, please archive the existing one.")
            % (self.company_id.name))


class HrLeavePolicy(models.Model):

    _name = "hr.leave.policy"
    _description = 'Leave Balance Matrix by Grade'

    @api.model
    def default_get(self, fields):
        res = super(HrLeavePolicy, self).default_get(fields)
        if 'line_ids' in fields and not res.get('line_ids'):
            res['line_ids'] = [
                (0, 0, {'month': '01', 'number_of_days': 1}),
                (0, 0, {'month': '02', 'number_of_days': 1}),
                (0, 0, {'month': '03', 'number_of_days': 1}),
                (0, 0, {'month': '04', 'number_of_days': 1}),
                (0, 0, {'month': '05', 'number_of_days': 1}),
                (0, 0, {'month': '06', 'number_of_days': 1}),
                (0, 0, {'month': '07', 'number_of_days': 1}),
                (0, 0, {'month': '08', 'number_of_days': 1}),
                (0, 0, {'month': '09', 'number_of_days': 1}),
                (0, 0, {'month': '10', 'number_of_days': 1}),
                (0, 0, {'month': '11', 'number_of_days': 1}),
                (0, 0, {'month': '12', 'number_of_days': 1})
            ]
        return res

    from_grade = fields.Many2one('hr.grade', string='From Grade')
    to_grade = fields.Many2one('hr.grade', string='To Grade')
    number_of_days = fields.Float('Total', compute="_compute_total_days", store=True)
    header_id = fields.Many2one('hr.leave.policy.header')
    line_ids = fields.One2many('hr.leave.policy.balance', 'policy_id', 'Balance per month')

    @api.depends('line_ids')
    def _compute_total_days(self):
        for rec in self:
            rec.number_of_days = 0
            for line in rec.line_ids:
                rec.number_of_days  += line.number_of_days

class HrLeaveBalance(models.Model):

    _name = "hr.leave.policy.balance"
    _description = 'Balance per month'

    policy_id = fields.Many2one('hr.leave.policy')
    month = fields.Selection([
        ('01', 'January'), ('02', 'February'), 
        ('03', 'March'), ('04', 'April'),
        ('05', 'May'), ('06', 'June'), 
        ('07', 'July'), ('08', 'August'), 
        ('09', 'September'), ('10', 'October'), 
        ('11', 'November'), ('12', 'December')], 
        string='Month')
    number_of_days = fields.Float('Number of Days')