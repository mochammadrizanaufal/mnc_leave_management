from odoo import models, fields, api, _
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_round
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
import re

import logging
from lxml import etree
import json

_logger = logging.getLogger(__name__)

class HolidaysAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    name = fields.Char('Description', compute='_compute_description', inverse='_inverse_description', search='_search_description', compute_sudo=False)
    description = fields.Char('Description')
    validity_start = fields.Date("Valid From")
    validity_stop = fields.Date("Valid To")
    extend_validity = fields.Date("Extend Until")
    extend_state = fields.Selection([
         ('no_request', 'No Request'),
         ('waiting', 'Waiting Approval'),
         ('approved', 'Approved'),
    ], default="no_request", string="Extend Request")


    def extend_request_btn(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Extend Date',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.leave.allocation.extend',
            'target': 'new',
        }

    @api.depends_context('uid')
    def _compute_description(self):
        for allocation in self:
            allocation.name = allocation.sudo().private_name
   
    def _inverse_description(self):
        for allocation in self:
            allocation.sudo().private_name = allocation.name

    def approve_extend_request(self):
        self.extend_state = 'approved'

    def refuse_extend_request(self):
        self.extend_state = 'no_request'
        self.extend_validity = False

    def action_approve(self):
        # if validation_type == 'both': this method is the first approval approval
        # if validation_type != 'both': this method calls action_validate() below
        if any(holiday.state != 'confirm' for holiday in self):
            raise UserError(_('Allocation request must be confirmed ("To Approve") in order to approve it.'))

        self.action_validate()
        self.activity_update()

    def _action_validate_create_childs(self):
        childs = self.env['hr.leave.allocation']
        leave_policy = self.env['hr.leave.policy.header'].search([('company_id', '=', self.mode_company_id.id),('active','=',True)])
        if self.state == 'validate' and self.holiday_type in ['category', 'department', 'company']:
            if self.holiday_type == 'category':
                employees = self.category_id.employee_ids
                self._validate_create_childs(childs, employees)
            elif self.holiday_type == 'department':
                employees = self.department_id.member_ids
                self._validate_create_childs(childs, employees)
            else:
                if not leave_policy:
                    raise ValidationError(_('Allocation Policy for %s not found. Please set it on Configuration > Time Off Allocation Policy.')
                    % (self.mode_company_id.name))

                for policy in leave_policy.matrix_ids:
                    policy_range = list(range(policy.from_grade.sequence, policy.to_grade.sequence + 1))
                    employees = self.env['hr.employee'].search([('company_id', '=', self.mode_company_id.id),('salary_grade_id.sequence', 'in', policy_range)])
                    self._validate_create_childs(childs, employees, policy)

        return childs

    def _validate_create_childs(self, childs, employees, policy=None):
        holiday_type_obj = self.env['hr.leave.type']
        holiday_type_name = self.holiday_status_id.name
        holiday_type_year = int(re.search(r'\d+', holiday_type_name).group()) - 1
        name_param = 'Annual Leave %s' % holiday_type_year
        hol_type = holiday_type_obj.search([('name', '=', name_param),('company_id', '=', self.mode_company_id.id)])

        for employee in employees:
            current_year = datetime.strftime(date.today(), '%Y')
            join_day = datetime.strftime(employee.date_join, '%d')
            join_month = datetime.strftime(employee.date_join, '%m')
            join_year = datetime.strftime(employee.date_join, '%Y')
            validity_year = datetime.strftime(self.holiday_status_id.validity_start, '%Y')
            yos = employee._get_years_of_joining()
            number_of_days = 0
            validity_start = self.holiday_status_id.validity_start
            validity_stop = self.holiday_status_id.validity_stop
            ydiff = int(validity_year) - int(join_year)
            
            if yos <= 1:
                if join_year == validity_year:
                    continue
                elif validity_year > current_year:
                    if ydiff < 2:
                        validity_start = employee.date_join + relativedelta(years=1)
                        number_of_days = self.compute_number_of_days(policy, join_month, join_day)
                    else:
                        number_of_days = policy.number_of_days
                else:
                    validity_start = employee.date_join + relativedelta(years=1)
                    number_of_days = self.compute_number_of_days(policy, join_month, join_day)
            else:
                number_of_days = policy.number_of_days

            if hol_type:
                mapped_days = hol_type.get_employees_days(employee.ids)
                remaining_days = mapped_days[employee.id][hol_type.id]

                if remaining_days['remaining_leaves'] < 0:
                    number_of_days = number_of_days - abs(remaining_days['remaining_leaves'] )

            childs += self.with_context(
                mail_notify_force_send=False,
                mail_activity_automation_skip=True
            ).create(self._prepare_holiday_values(employee, policy, number_of_days, validity_start, validity_stop))
        self.validity_start = self.holiday_status_id.validity_start
        self.validity_stop = self.holiday_status_id.validity_stop
        childs.action_approve()
        for child in childs:
            child.holiday_status_id._subtract_balance(child)
        return childs

    def compute_number_of_days(self, policy, join_month, join_day):
        number_of_days = 0
        for line in policy.line_ids:
            if line.month >= join_month:
                number_of_days += line.number_of_days
            if line.month == join_month and join_day > '15':
                number_of_days = number_of_days - line.number_of_days
        return number_of_days
    
    def _prepare_holiday_values(self, employee, policy=None, number_of_days=None, validity_start=None, validity_stop=None):
        self.ensure_one()

        values = {
            'name': self.holiday_status_id.name + ' allocation for ' + employee.name if self.holiday_type == 'company' else self.name,
            'holiday_type': 'employee',
            'holiday_status_id': self.holiday_status_id.id,
            'notes': self.notes,
            'number_of_days': number_of_days if self.holiday_type == 'company' else self.number_of_days,
            'parent_id': self.id,
            'employee_id': employee.id,
            'allocation_type': 'regular',
            'date_to': self.date_to,
            'interval_unit': self.interval_unit,
            'interval_number': self.interval_number,
            'number_per_interval': self.number_per_interval,
            'unit_per_interval': self.unit_per_interval,
            'validity_start': validity_start if validity_start else False,
            'validity_stop': validity_stop if validity_stop else False
        }
        return values

    def name_get(self):
        res = []
        if self._context.get('get_alloc_days'):
            for rec in self:
                for record in rec.holiday_status_id:
                    name = record.name
                    if record.allocation_type != 'no':
                        name = "%(name)s (%(count)s)" % {
                            'name': name,
                            'count': _('%g remaining out of %g') % (
                                float_round(record.virtual_remaining_leaves, precision_digits=2) or 0.0,
                                float_round(record.max_leaves, precision_digits=2) or 0.0,
                            ) + (_(' hours') if record.request_unit == 'hour' else _(' days'))
                        }
                    res.append((rec.id, name))
        elif self._context.get('get_alloc_days_form'):
            for rec in self:
                for record in rec.holiday_status_id:
                    name = record.name
                    if record.allocation_type != 'no':
                        name = "%(name)s" % {
                            'name': name
                        }
                    res.append((rec.id, name))
        else:
            for allocation in self:
                if allocation.holiday_type == 'company':
                    target = allocation.mode_company_id.name
                    res.append(
                        (allocation.id,
                        _("Allocation of %(allocation_name)s to %(person)s",
                        allocation_name=allocation.holiday_status_id.sudo().name,
                        person=target
                        ))
                    )
                else:
                    if allocation.holiday_type == 'department':
                        target = allocation.department_id.name
                    elif allocation.holiday_type == 'category':
                        target = allocation.category_id.name
                    else:
                        target = allocation.employee_id.sudo().name
                    res.append(
                        (allocation.id,
                        _("Allocation of %(allocation_name)s : %(duration).2f %(duration_type)s to %(person)s",
                        allocation_name=allocation.holiday_status_id.sudo().name,
                        duration=allocation.number_of_hours_display if allocation.type_request_unit == 'hour' else allocation.number_of_days,
                        duration_type='hours' if allocation.type_request_unit == 'hour' else 'days',
                        person=target
                        ))
                    )
        return res


    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(HolidaysAllocation, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])

        view_types = [
            "/tree",
            "/form"
        ]

        for view in view_types:
            for node in doc.xpath(view):
                if not self.env.user.has_group("hr_holidays.group_hr_holidays_manager"):

                    modifiers = json.loads(node.get('create', 'false'))
                    node.set('create', json.dumps(modifiers))

                    modifiers = json.loads(node.get('edit', 'false'))
                    node.set('edit', json.dumps(modifiers))

        res['arch'] = etree.tostring(doc)
        return res

class ExtendValidity(models.TransientModel):
    _name = 'hr.leave.allocation.extend'
    _description = 'Extend Allocation Validity'

    extend_validity = fields.Date("Extend Until")

    def btn_send_request(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids')
        allocation = self.env['hr.leave.allocation'].search([
            ('id', '=', active_ids[0]),
        ])
        allocation.extend_validity = self.extend_validity
        allocation.extend_state = 'waiting'
        self.send_email_extend_request(allocation)

    def send_email_extend_request(self, allocation):  
        message_obj = self.env['mail.message']
        mail_obj = self.env['mail.mail']
        mail_server = self.env['ir.mail_server'].sudo().search([])
        superior = allocation.holiday_status_id.responsible_id

        if superior:
            message_id = message_obj.create(
                {
                'message_type' : 'email',
                'subject' : "%s's Extend Allocation Request for %s until %s" % (
                                                                allocation.employee_id.name, 
                                                                allocation.holiday_status_id.name, 
                                                                self.extend_validity.strftime(DF)
                                                            ),
                }
            ) 

            mail_body = self.generate_mail_body_html(superior, allocation)
            mail_id = mail_obj.sudo().create({
                'mail_message_id' : message_id.id,
                'state' : 'outgoing',
                'auto_delete' : True,
                'mail_server_id': mail_server[0].id,
                'email_from' : 'no-reply@mncgroup.com',
                'email_to' : superior.work_email,
                'reply_to' : 'no-reply@mncgroup.com',
                'body_html' : mail_body})
            mail_id.sudo().send()

    def generate_mail_body_html(self, superior, allocation):
        html =  """
<p style="margin:0px 0px 10px 0px;"></p>
<div style="font-family: 'Lucida Grande', Ubuntu, Arial, Verdana, sans-serif; font-size: 12px; color: rgb(34, 34, 34); background-color: #FFF; ">
    <p style="margin:0px 0px 10px 0px;font-weight: bold">Hello Mr / Mrs %s,</p>""" % (superior.employee_id.name)


        html +="""
    <p style="margin:0px 0px 10px 0px;">
    Please kindly approve the following extend validity request,
    <p style="margin:0px 0px 10px 0px;">
        Time Off Type : %s
        <br/>
        Extend Until: %s

    </p>""" % (
        self.generate_hyperlink(allocation), 
        self.extend_validity.strftime(DF)
        )

        html +="""
    <p style='margin:0px 0px 10px 0px;font-size:13px;font-family:"Lucida Grande", Helvetica, Verdana, Arial, sans-serif;'>Thank you.</p>
</div>"""

        return html

    def generate_hyperlink(self, allocation):
        action_id = self.env.ref('hr_holidays.hr_leave_allocation_action_approve_department').id
        menu_id = self.env.ref('mnc_leave_management.menu_approve_all_allocations').id
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        ir_model_data = self.env['ir.model.data']
        base = '/web#'
        web_url = base_url + base +'action='+str(action_id)+'&'+'cids='+str(allocation.employee_id.company_id.id)+'&'+'id='+str(allocation.id)+'&'+'menu_id='+str(menu_id)+'&'+'model='+'hr.leave.allocation'+'&'+'view_type=form'
        web_hyperlink =  """<a href=%s > %s </a> """ % (web_url,allocation.name)
        return """
        
        <p style='margin:0px 0px 10px 0px;font-size:13px;font-family:"Lucida Grande", Helvetica, Verdana, Arial, sans-serif;'>
            %s
        </p>
        
        """ % (web_hyperlink)
