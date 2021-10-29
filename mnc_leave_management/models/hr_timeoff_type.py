from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
import logging
_logger = logging.getLogger(__name__)

def get_selection_label(self, object, field_name, field_value):
    return _(dict(self.env[object].fields_get(allfields=[field_name])[field_name]['selection'])[field_value])

class HrTimeoffType(models.Model):
    _inherit = "hr.leave.type"

    name = fields.Char('Time Off Type', required=False)
    time_off_type = fields.Selection([
        ('paid', 'Paid Leave'),
        ('sick', 'Sick Permit'),
        ('compensatory', 'Compensatory'),
        ('unpaid', 'Unpaid'),
    ], default="paid", string="Time Off Type")
    mass_leave_ids = fields.One2many('hr.mass.leave', 'leave_type_id', 'Mass Leave Date')

    @api.model
    def create(self,vals):
        res = super(HrTimeoffType,self).create(vals)
        time_off_type = get_selection_label(self, 'hr.leave.type','time_off_type',res.time_off_type)
        if res.time_off_type == 'paid':
            valid_year = datetime.strftime(res.validity_start, '%Y')
            name = "%s %s" % (time_off_type, valid_year)
        else:
            name = "%s" % time_off_type
        res.name = name
        return res

    @api.onchange('time_off_type')
    def onchange_type(self):
        if self.time_off_type == 'paid':
            self.allocation_type = 'fixed'
            self.leave_validation_type = 'both'
            self.color_name = 'lightblue'
        else:
            self.allocation_type = 'no'
            self.leave_validation_type = 'both'

            if self.time_off_type == 'sick':
                self.color_name = 'magenta'

            if self.time_off_type == 'compensatory':
                self.color_name = 'lightyellow'

            if self.time_off_type == 'unpaid':
                self.color_name = 'red'

    def _subtract_balance(self, allocation):
        leave_obj = self.env['hr.leave']
        today = date.today()

        for mass_leave in self.mass_leave_ids:
            if mass_leave.date >= allocation.employee_id.date_join:
                values = {
                    'allocation_id': allocation.id,
                    'holiday_status_id': self.id,
                    'holiday_type': 'employee',
                    'employee_id': allocation.employee_id.id,
                    'name': mass_leave.name,
                    'request_date_from': mass_leave.date,
                    'request_date_to': mass_leave.date,
                    'date_from': mass_leave.date.strftime('%Y-%m-%d 01:00:00'),
                    'date_to': mass_leave.date.strftime('%Y-%m-%d 10:00:00'),
                }
                leave = leave_obj.create(values)
                leave.sudo().action_approve()
                leave.sudo().action_validate()


class HrHoliday(models.Model):
    _name = 'hr.mass.leave'
    _description = 'Mass Leave Dates'

    name = fields.Char('Description')
    date = fields.Date('Date')
    leave_type_id = fields.Many2one('hr.leave.type')
