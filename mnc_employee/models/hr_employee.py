from odoo import models, fields, api
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

import logging
from lxml import etree

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    #Position Information
    # job_id = fields.Char(string='Job Position')
    # department_id = fields.Char(string='Organization')
    department_id = fields.Many2one('hr.department', string='Organization')
    job_id = fields.Many2one('hr.job', 'Job Position', groups="hr.group_hr_user")
    job_title_id = fields.Char(string='Job Function', copy=False, groups="hr.group_hr_user")
    job_group_id = fields.Char(string='Job Group', groups="hr.group_hr_user")
    job_name_id = fields.Char(string='Job Name', groups="hr.group_hr_user")
    salary_grade_id = fields.Many2one('hr.grade', 'Grade', groups="hr.group_hr_user")
    level_id = fields.Many2one('hr.level', 'Level', ondelete='restrict', related='salary_grade_id.level_id', groups="hr.group_hr_user")
    location_id = fields.Char(string='Location', groups="hr.group_hr_user")
    parent_id = fields.Many2one('hr.employee', 'Superior', compute="_compute_parent_id", store=True, readonly=False,
        domain="[]", groups="hr.group_hr_user")
    superior_ids = fields.One2many('hr.superior', 'employee_id', 'Superiors')
    superior_ids_many2many = fields.One2many('hr.superior', 'employee_id', 'Superiors', related="superior_ids")
                                
    #Status Information
    employee_main_id = fields.Char('NIK', copy=False, groups="hr.group_hr_user")
    person_id = fields.Char('Person ID', copy=False, groups="hr.group_hr_user")
    employment_status_id = fields.Char(string='Employment Status', copy=False, groups="hr.group_hr_user")
    date_join = fields.Date('Join Group Date', copy=False, groups="hr.group_hr_user")
    date_resign = fields.Date('Resign Date', copy=False, groups="hr.group_hr_user")
    date_permanent = fields.Date('Permanent Date', copy=False, groups="hr.group_hr_user")
    years_of_service = fields.Float('Total Years of Service',
                                    compute='_get_years_of_service', groups="hr.group_hr_user")
    years_of_joining = fields.Float('Total Years of Joining',
                                    compute='_get_years_of_joining', groups="hr.group_hr_user")
    year_join = fields.Integer('Years of Joining', compute='_get_years_of_joining', groups="hr.group_hr_user")
    month_join = fields.Integer('Months of Joining', compute='_get_years_of_joining', groups="hr.group_hr_user")
    year_service = fields.Integer('Years of Service', compute='_get_years_of_service', groups="hr.group_hr_user")
    month_service = fields.Integer('Months of Service', compute='_get_years_of_service', groups="hr.group_hr_user")

    #KTP Information
    religion_id = fields.Char('Religion', copy=False, groups="hr.group_hr_user")
    family_card_number = fields.Char('No Kartu Keluarga', copy=False, groups="hr.group_hr_user")
    identification_id = fields.Char(string='No KTP', copy=False, groups="hr.group_hr_user")
    ktp_street = fields.Char('KTP Address', groups="hr.group_hr_user")
    ktp_street2 = fields.Char('KTP Address Line 2', groups="hr.group_hr_user")
    ktp_zip = fields.Char('KTP Postal Code', groups="hr.group_hr_user")
    ktp_city = fields.Char('KTP City', groups="hr.group_hr_user")
    ktp_state_id = fields.Many2one('res.country.state', 'KTP Province', groups="hr.group_hr_user")
    blood_type = fields.Selection([
        ('A', 'A'),
        ('B', 'B'),
        ('AB', 'AB'),
        ('O', 'O'),
    ], 'Blood Type', groups="hr.group_hr_user")

    #Domicile Address
    street = fields.Char('Address Line 1', groups="hr.group_hr_user")
    street2 = fields.Char('Address Line 2', groups="hr.group_hr_user")
    zip = fields.Char('Postal Code', groups="hr.group_hr_user")
    city = fields.Char('City', groups="hr.group_hr_user")
    state_id = fields.Many2one('res.country.state', 'Province',
                               ondelete='restrict', groups="hr.group_hr_user")
    address_country_id = fields.Many2one('res.country', 'Country',
                                         ondelete='restrict', groups="hr.group_hr_user")

    #Birthday
    age = fields.Integer('Age', compute='_compute_age', store=True, groups="hr.group_hr_user")

    #Family Information
    marital_status_id = fields.Char(string='Marital Status', groups="hr.group_hr_user")
    family_member_ids = fields.One2many('hr.family.member', 'employee_id',
                                        'Family Member', groups="hr.group_hr_user")
    emergency_contact_ids = fields.One2many(
        'hr.emergency.contact', 'employee_id', 'Emergency Contact', groups="hr.group_hr_user")

    #Education
    institution_id = fields.Char(string='Institution', groups="hr.group_hr_user")
    faculty_id = fields.Char(string='Faculty', groups="hr.group_hr_user")
    major_id = fields.Char(string='Major', groups="hr.group_hr_user")
    education_level_id = fields.Char(string='Education Level', groups="hr.group_hr_user")

    #Tax Information
    has_npwp = fields.Boolean('Has NPWP', default=True, groups="hr.group_hr_user")
    npwp_name = fields.Char('NPWP Name', copy=False, groups="hr.group_hr_user")
    npwp = fields.Char('NPWP', copy=False, groups="hr.group_hr_user")
    npwp_address = fields.Char('NPWP Address', copy=False, groups="hr.group_hr_user")
    ptkp_id = fields.Char(string='Active PTKP', groups="hr.group_hr_user")
    status_ptkp_id = fields.Char(string='Family Status', groups="hr.group_hr_user")

    #Insurance Information
    no_bpjs_kesehatan = fields.Char('No BPJS Kesehatan', copy=False, groups="hr.group_hr_user")
    no_bpjs_ketenagakerjaan = fields.Char('No BPJS Ketenagakerjaan', copy=False, groups="hr.group_hr_user")
    no_bpjs_pensiun = fields.Char('No BPJS Pensiun', copy=False, groups="hr.group_hr_user")
    no_dplk = fields.Char('No DPLK', copy=False, groups="hr.group_hr_user")

    #Methods

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self.env.context.get('manager_form'):
            superior = self.env['hr.superior'].search([('parent_id.user_id', '=', self.env.user.id)])
            args += [('id', 'in', superior.employee_id.ids)]

        return super(HrEmployee, self).search(args, offset, limit, order, count=count)

    @api.depends('superior_ids')
    def _compute_parent_id(self):
        for superior in self.superior_ids:
            if superior.is_main:
                self.parent_id = superior.parent_id

    @api.constrains('superior_ids')
    def constraint_superior(self):
        if self.superior_ids:
            main = []
            for superior in self.superior_ids:
                if superior.is_main:
                    main += superior
            if len(main) < 1:
                raise ValidationError("Please set a main superior")
            if len(main) > 1:
                raise ValidationError("Can only set one main superior")

    @api.depends('birthday')
    def _compute_age(self):
        for rec in self:
            if rec.birthday:
                rec.age = relativedelta(date.today(), rec.birthday).years

    @api.depends('education_ids')
    def _get_education(self):
        """ compute function to get latest education """
        for rec in self:
            if rec.education_ids:
                educations = rec.education_ids.sorted(key=lambda x: x.date_to)
                if educations:
                    last = educations[0]
                    rec.institution_id = last.institution_id.id
                    rec.faculty_id = last.faculty_id.id
                    rec.major_id = last.major_id.id
                    rec.education_level_id = last.education_level_id.id

    @api.depends('date_permanent')
    def _get_years_of_service(self):
        for rec in self:
            year = 0
            month = 0
            rec.year_service = 0
            rec.month_service = 0
            rec.years_of_service = 0
            if rec.date_permanent:
                yos = relativedelta(date.today(), rec.date_permanent)
                year = yos.years
                month = yos.months
                rec.year_service = year
                rec.month_service = month
                year += month / 12
                rec.years_of_service = year

    @api.depends('date_join')
    def _get_years_of_joining(self):
        for rec in self:
            yos = 0
            year = 0
            month = 0
            rec.year_join = 0
            rec.month_join = 0
            rec.years_of_joining = 0
            if rec.date_join:
                _logger.info('datejoin: %s', rec.date_join)
                yos = relativedelta(date.today(), rec.date_join)
                year = yos.years
                month = yos.months
                rec.year_join = year
                rec.month_join = month
                year += month / 12
                yos = rec.years_of_joining = year
                return yos
