from odoo import api, fields, models


class HrFamilyMember(models.Model):
    _name = 'hr.family.member'
    _description = 'Family Member'

    employee_id = fields.Many2one('hr.employee', 'Employee', ondelete='cascade')
    name = fields.Char('Name', required=True)
    relation_id = fields.Char(string='Relationship')
    ktp = fields.Char('KTP', copy=False)
    passport = fields.Char('Passport', copy=False)
    phone = fields.Char('Phone')
    birthday = fields.Date('Birthday')
    occupation = fields.Char('Occupation')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], 'Gender', default='male')
    marital = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('cohabitant', 'Legal Cohabitant'),
        ('widower', 'Widower'),
        ('divorced', 'Divorced')
    ], 'Marital Status', default='single')
    religion_id = fields.Char(string='Religion')
    last_education_id = fields.Char(string='Last Education Level')
    place_of_birth = fields.Char('Place Of Birth')
    street = fields.Char('Address')
    street2 = fields.Char('Address Line 2')
    zip = fields.Char('Postal Code')
    city = fields.Char('City')
    state_id = fields.Many2one('res.country.state', 'Province',
                               ondelete='restrict')
    country_id = fields.Many2one('res.country', 'Country', ondelete='restrict')


    # @api.onchange('phone')
    # def _onchange_phone(self):
    #     if self.phone and not self.phone.isdigit():
    #         return {
    #             'value': {
    #                 'phone': '',
    #             },
    #             'warning': {
    #                 'title': 'Invalid',
    #                 'message': 'Phone must contain only numbers!'
    #             }
    #         }

    # @api.onchange('ktp')
    # def _onchange_ktp(self):
    #     if self.ktp and (not self.ktp.isdigit() or len(self.ktp) != 16):
    #         return {
    #             'value': {
    #                 'ktp': '',
    #             },
    #             'warning': {
    #                 'title': 'Invalid',
    #                 'message': 'KTP must contain only numbers and 16 digits!'
    #             }
    #         }


class HrEmergencyContact(models.Model):
    _name = 'hr.emergency.contact'
    _description = 'Emergency Contact'

    name = fields.Char('Name')
    employee_id = fields.Many2one('hr.employee', 'Employee', ondelete='cascade')
    street = fields.Char('Address Line 1')
    street2 = fields.Char('Address Line 2')
    postal = fields.Char('Postal Code')
    city = fields.Char('City')
    state_id = fields.Many2one('res.country.state', 'State', copy=False,
                               ondelete='set null')
    country_id = fields.Many2one('res.country', 'Country', copy=False,
                                 ondelete='set null')
    zip = fields.Char('Zip')
    phone = fields.Char('Phone')
    mobile = fields.Char('Mobile Phone (1)')
    mobile_secondary = fields.Char('Mobile Phone (2)')
    email = fields.Char('Email')
    relation_id = fields.Char(string='Relationship')

    # @api.onchange('phone')
    # def _onchange_phone(self):
    #     if self.phone and not self.phone.isdigit():
    #         return {
    #             'value': {
    #                 'phone': '',
    #             },
    #             'warning': {
    #                 'title': 'Invalid',
    #                 'message': 'Phone must contain only numbers!'
    #             }
    #         }

    # @api.onchange('mobile')
    # def _onchange_mobile(self):
    #     if self.mobile and not self.mobile.isdigit():
    #         return {
    #             'value': {
    #                 'mobile': '',
    #             },
    #             'warning': {
    #                 'title': 'Invalid',
    #                 'message': 'Mobile Phone(1) must contain only numbers!'
    #             }
    #         }

    # @api.onchange('mobile_secondary')
    # def _onchange_mobile_secondary(self):
    #     if self.mobile_secondary and not self.mobile_secondary.isdigit():
    #         return {
    #             'value': {
    #                 'mobile_secondary': '',
    #             },
    #             'warning': {
    #                 'title': 'Invalid',
    #                 'message': 'Mobile Phone(2) must contain only numbers!'
    #             }
    #         }
