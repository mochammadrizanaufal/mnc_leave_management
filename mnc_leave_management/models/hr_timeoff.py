from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import ValidationError
from odoo.tools import float_compare
from odoo.addons.hr_holidays.models.hr_leave import HolidaysRequest as HrLeaveRequest

import re
import logging
import os
import requests
from lxml import etree
import json
_logger = logging.getLogger(__name__)

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    allocation_id = fields.Many2one('hr.leave.allocation', string='Allocation')
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('cancel', 'Cancelled'), 
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Approved'),
        ('validate', 'Released')
        ], string='Status', default='draft', compute="",tracking=True, copy=False, store=True, readonly=False,
        help="The status is set to 'To Submit', when a time off request is created." +
        "\nThe status is 'To Approve', when time off request is confirmed by user." +
        "\nThe status is 'Refused', when time off request is refused by manager." +
        "\nThe status is 'Approved', when time off request is approved by manager." +
        "\nThe status is 'Released', when leave request is verified by HR admin.")
    attachment_id = fields.Binary(string='Attachment')
    is_mass_leave = fields.Boolean(string='Is Mass Leave')
    require_attachment = fields.Boolean("Require Attachment", related='holiday_status_id.require_attachment')
    name = fields.Char('Reason', compute='_compute_description', inverse='_inverse_description', search='_search_description', compute_sudo=False)

    @api.depends_context('uid')
    def _compute_description(self):
        for leave in self:
            leave.name = leave.sudo().private_name

    def _inverse_description(self):
        for leave in self:
            leave.sudo().private_name = leave.name


    @api.constrains('state', 'number_of_days', 'holiday_status_id')
    def _check_holidays(self):
        mapped_days = self.mapped('holiday_status_id').get_employees_days(self.mapped('employee_id').ids)
        for holiday in self:
            if holiday.holiday_type != 'employee' or not holiday.employee_id or holiday.holiday_status_id.allocation_type == 'no' or holiday.is_mass_leave:
                continue
            leave_days = mapped_days[holiday.employee_id.id][holiday.holiday_status_id.id]
            if float_compare(leave_days['remaining_leaves'], 0, precision_digits=2) == -1 or float_compare(leave_days['virtual_remaining_leaves'], 0, precision_digits=2) == -1:
                raise ValidationError(_('The number of remaining time off is not sufficient for this time off type.\n'))
              

    @api.model
    def default_get(self, fields_list):
        defaults = super(HrLeaveRequest, self).default_get(fields_list)
        defaults['state'] = 'draft'
        return defaults

    @api.onchange('allocation_id')
    def onchange_allocation(self):
        self.holiday_status_id = self.allocation_id.holiday_status_id

    @api.constrains('allocation_id', 'date_to', 'date_from')
    def _check_leave_type_validity(self):
        for leave in self:
            vstart = leave.allocation_id.validity_start
            vextend = leave.allocation_id.extend_validity
            dfrom = leave.date_from
            dto = leave.date_to

            if leave.allocation_id.extend_state != 'approved':
                vstop = leave.allocation_id.validity_stop
            else:
                vstop = leave.allocation_id.extend_validity

            if vstart and vstop:
                if dfrom and dto and (dfrom.date() < vstart or dto.date() > vstop):
                    raise ValidationError(_(
                        '%(leave_type)s are only valid between %(start)s and %(end)s',
                        leave_type=leave.holiday_status_id.display_name,
                        start=vstart,
                        end=vstop
                    ))


    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(HrLeave, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        fields = [
            "//field[@name='allocation_id']",
            "//field[@name='holiday_status_id']", 
            "//field[@name='request_date_from']", 
            "//field[@name='request_date_to']",
            "//field[@name='request_unit_half']",
            "//field[@name='name']"
            ]

        admin_fields = [
            "//field[@name='allocation_id']",
            "//field[@name='holiday_status_id']",
            "//field[@name='number_of_days']",
            "//field[@name='name']"
        ]

        view_types = [
            "/tree",
            "/form"
        ]

        for field in fields:
            for node in doc.xpath(field):
                if not self.env.user.has_group("hr_holidays.group_hr_holidays_responsible"):
                    modifiers = json.loads(node.get('modifiers', '{}'))
                    modifiers['readonly'] = "[('state', '!=', 'draft')]"
                    node.set('modifiers', json.dumps(modifiers))

        # for field in admin_fields:
        #     for node in doc.xpath(field):
        #         modifiers = json.loads(node.get('modifiers', '{}'))
        #         modifiers['readonly'] = "[('state', 'in', ('validate1','validate'))]"
        #         node.set('modifiers', json.dumps(modifiers))

        res['arch'] = etree.tostring(doc)
        return res

    def action_confirm(self):
        if self.holiday_status_id.time_off_type == 'permit' and self.holiday_status_id.use_max_permit:
            permits = self.search([('holiday_status_id', '=', self.holiday_status_id.id),('employee_id', '=', self.employee_id.id)])
            sum_days = 0
            for permit in permits:
                sum_days += permit.number_of_days
            if sum_days > self.holiday_status_id.max_permit:
                raise ValidationError(_('Permit taken exceeds limit.'))

        if self.filtered(lambda holiday: holiday.state != 'draft'):
            raise UserError(_('Time off request must be in Draft state ("To Submit") in order to confirm it.'))
        self.send_email_leave_request()
        self.write({'state': 'confirm'})
        holidays = self.filtered(lambda leave: leave.validation_type == 'no_validation')
        if holidays:
            # Automatic validation should be done in sudo, because user might not have the rights to do it by himself
            holidays.sudo().action_validate()

        for holiday in self.filtered(lambda holiday: holiday.employee_id.user_id):
            holiday.sudo().message_post(
                body=_(
                    'Your %(leave_type)s request planned on %(date)s has been notified to Mr./Mrs. %(superior)s',
                    leave_type=holiday.holiday_status_id.display_name,
                    date=holiday.date_from,
                    superior=holiday.employee_id.parent_id.user_id.name
                ),
                partner_ids=holiday.parent_id.employee_id.user_id.partner_id.ids)
        return True

    def action_approve(self):
        # if validation_type == 'both': this method is the first approval approval
        # if validation_type != 'both': this method calls action_validate() below
        if any(holiday.state != 'confirm' for holiday in self):
            raise UserError(_('Time off request must be confirmed ("To Approve") in order to approve it.'))
        if not self.env.context.get('skip_mail_notif'):
            self.send_email_leave_request()
        current_employee = self.env.user.employee_id
        self.filtered(lambda hol: hol.validation_type == 'both').write({'state': 'validate1', 'first_approver_id': current_employee.id})

        # Post a second message, more verbose than the tracking message
        for holiday in self.filtered(lambda holiday: holiday.employee_id.user_id):
            holiday.sudo().message_post(
                body=_(
                    'Your %(leave_type)s planned on %(date)s has been accepted',
                    leave_type=holiday.holiday_status_id.display_name,
                    date=holiday.date_from
                ),
                partner_ids=holiday.employee_id.user_id.partner_id.ids)
        self.filtered(lambda hol: not hol.validation_type == 'both').action_validate()

        return True

    def send_email_leave_request(self):  
        message_obj = self.env['mail.message']
        mail_obj = self.env['mail.mail']
        mail_server = self.env['ir.mail_server'].sudo().search([])
        if self.state == 'draft':
            if self.employee_id.parent_id:
                superior = self.employee_id.parent_id.user_id
            else:
                superior = self.holiday_status_id.responsible_id
        else:
            superior = self.holiday_status_id.responsible_id

        if superior:
            message_id = message_obj.create(
                {
                'message_type' : 'email',
                'subject' : "%s's %s Request from %s to %s" % (
                                                                self.employee_id.name, 
                                                                self.holiday_status_id.name, 
                                                                self.request_date_from.strftime(DF), 
                                                                self.request_date_to.strftime(DF)
                                                            ),
                }
            ) 
            _logger.info('email: %s', superior.work_email)
            mail_body = self.generate_mail_body_html(superior)
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

    def generate_mail_body_html(self, superior):
        html =  """
<p style="margin:0px 0px 10px 0px;"></p>
<div style="font-family: 'Lucida Grande', Ubuntu, Arial, Verdana, sans-serif; font-size: 12px; color: rgb(34, 34, 34); background-color: #FFF; ">
    <p style="margin:0px 0px 10px 0px;font-weight: bold">Hello Mr / Mrs %s,</p>""" % (superior.employee_id.name)


        html +="""
    <p style="margin:0px 0px 10px 0px;">
    Please kindly %s the following %s request,
    <p style="margin:0px 0px 10px 0px;">
        %s
        From : %s
        <br/>
        To : %s
        <br/>
        Reason : %s
    </p>""" % (
        'approve' if self.state == 'draft' else 'release',
        'leave' if self.holiday_status_id.time_off_type == 'paid' else 'permit',
        self.generate_hyperlink(), 
        self.request_date_from.strftime(DF), 
        self.request_date_to.strftime(DF),
        self.name
        )

        html +="""
    <p style='margin:0px 0px 10px 0px;font-size:13px;font-family:"Lucida Grande", Helvetica, Verdana, Arial, sans-serif;'>Thank you.</p>
</div>"""

        return html

    def generate_hyperlink(self):
        if self.state == 'draft':
            action_id = self.env.ref('mnc_leave_management.hr_leave_action_approve_managed_employee').id
            menu_id = self.env.ref('hr_holidays.menu_open_department_leave_approve').id
        else:
            action_id = self.env.ref('hr_holidays.hr_leave_action_action_approve_department').id
            menu_id = self.env.ref('mnc_leave_management.menu_open_all_leave_approve').id
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        ir_model_data = self.env['ir.model.data']
        base = '/web#'
        web_url = base_url + base +'action='+str(action_id)+'&'+'cids='+str(self.employee_id.company_id.id)+'&'+'id='+str(self.id)+'&'+'menu_id='+str(menu_id)+'&'+'model='+'hr.leave'+'&'+'view_type=form'
        web_hyperlink =  """<a href=%s > %s on %s : %s day(s) </a> """ % (web_url,self.employee_id.name, self.holiday_status_id.name, self.number_of_days)
        return """
        
        <p style='margin:0px 0px 10px 0px;font-size:13px;font-family:"Lucida Grande", Helvetica, Verdana, Arial, sans-serif;'>
            %s
        </p>
        
        """ % (web_hyperlink)

    def write(self, values):
        employee_id = values.get('employee_id', False)
        if not self.env.context.get('leave_fast_create'):
            if values.get('state'):
                self._check_approval_update(values['state'])
                if any(holiday.validation_type == 'both' for holiday in self):
                    if values.get('employee_id'):
                        employees = self.env['hr.employee'].browse(values.get('employee_id'))
                    else:
                        employees = self.mapped('employee_id')
                    self._check_double_validation_rules(employees, values['state'])
            if 'date_from' in values:
                values['request_date_from'] = values['date_from']
            if 'date_to' in values:
                values['request_date_to'] = values['date_to']
        result = super(HrLeaveRequest, self).write(values)
        if not self.env.context.get('leave_fast_create'):
            for holiday in self:
                if employee_id:
                    holiday.add_follower(employee_id)
        return result

#     def _send_notif_telegram(self, leave):
#         telegram_api_url = self.env['ir.config_parameter'].sudo().get_param('hris.telegram_api_url')
#         token_bot = self.env['ir.config_parameter'].sudo().get_param('hris.telegram_bot_token')
#         if not token_bot:
#             raise UserError(_('please fill token bot parameter'))
#         url = os.path.join(telegram_api_url, 'bot{token}'.format(token=token_bot)).replace('\\', '/')
#         employee = leave.employee_id
#         second_approver_ids = self.env.ref('hr_holidays.group_hr_holidays_manager').users
#         managers = second_approver_ids if self.env.context.get('second_approve') else employee.leave_manager_id

#         for manager in managers:
#             message = """
# Hello Mr / Mrs %s,
# Please kindly review the following %s request from %s

# Dates: %s to %s
# Duration: %s day(s)
# Reason: %s

# Thank you.
#                 """ % (manager.partner_id.name, 
#                 leave.holiday_status_id.name, employee.name, 
#                 leave.request_date_from, leave.request_date_to,
#                 leave.number_of_days,
#                 leave.name)
#             data = {
#                 'chat_id': '@darthriza',
#                 'text': message,
#                 'reply_markup': {
#                     'inline_keyboard': [
#                         [{'text': 'Approve', 'callback_data': 't|%s' % leave.id},
#                         {'text': 'Refuse', 'callback_data': 'f|%s' % leave.id}]
#                     ]
#                 }
#             }
#             resp = requests.post(url + '/sendMessage', json=data)
#             if not resp.ok:
#                 raise UserError(_(resp.text))
#             return True

#     @api.model_create_multi
#     def create(self, vals_list):
#         res = super(HrLeave, self).create(vals_list)
#         for leave in res:
#             leave_sudo = leave.sudo()
#             if leave.validation_type == 'manager' or leave.validation_type == 'both':
#                 leave_sudo._send_notif_telegram(leave)
#         return res

#     def action_approve(self):
#         res = super(HrLeave, self).action_approve()
#         if self.validation_type == 'both':
#             self.with_context(second_approve=True)._send_notif_telegram(self)
#         return res

