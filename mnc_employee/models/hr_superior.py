from odoo import api, fields, models


class HrSuperior(models.Model):
    _name = 'hr.superior'
    _description = 'Employee Superior'

    name = fields.Char("Name", compute="_get_name", store=True)
    employee_id = fields.Many2one('hr.employee', 'Employee',
                                  ondelete='restrict')
    parent_id = fields.Many2one('hr.employee', 'Superior')
    position_id = fields.Many2one('hr.job', 'Superior Position',
                                  related='parent_id.job_id',
                                  ondelete='restrict')
    is_main = fields.Boolean('Main Superior', default=False,
                             help='Check if it is main superior')
    category = fields.Selection([
        ('reporting', 'Reporting Manager Unit'),
        ('project', 'Project'),
    ], 'Superior Category', default='reporting')

    @api.depends('parent_id')
    def _get_name(self):
        for rec in self:
            rec.name = rec.parent_id.name
