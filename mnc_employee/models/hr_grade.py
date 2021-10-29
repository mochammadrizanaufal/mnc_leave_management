from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrMasterMixin(models.AbstractModel):
    _name = 'hr.master.mixin'
    _description = 'Mixin for Master Data'

    name = fields.Char('Name', copy=True)
    code = fields.Char('Code', copy=True)
    note = fields.Text('Note')
    active = fields.Boolean('Active', default=True)

    # def copy(self, default=None):
    #     self.ensure_one()
    #     name = default.get('name') if default else ''
    #     code = default.get('code') if default else ''
    #     new_name = name or _('%sCOPY') % self.name
    #     new_code = code or _('%sCOPY') % self.code
    #     default = dict(default or {}, name=new_name, code=new_code)
    #     return super(HrMasterMixin, self).copy(default)

    # @api.constrains('code')
    # def _check_code(self):
    #     domain = [('code', '=ilike', self.code), ('id', '!=', self.id)]
    #     rec = self.search(domain)
    #     if rec:
    #         raise ValidationError('Code already exists!')

class HrGrade(models.Model):
    _name = 'hr.grade'
    _inherit = 'hr.master.mixin'
    _description = 'Employee Grade'

    level_id = fields.Many2one('hr.level', 'Level', ondelete='set null')
    sequence = fields.Integer('Sequence', default=1)
    amount = fields.Float('amount')

    def name_get(self):
        """ function to get name for record """
        res = []
        for rec in self:
            name = '%s - %s' % (str(rec.sequence), rec.level_id.name)
            res.append((rec.id, name))
        return res

class HrLevel(models.Model):
    _name = 'hr.level'
    _inherit = 'hr.master.mixin'
    _description = 'Level'