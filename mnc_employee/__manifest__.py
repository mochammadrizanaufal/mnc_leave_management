# -*- coding: utf-8 -*-
{
    'name': "Self Service Employee Data",

    'summary': """
        Employee data self service""",

    'description': """
        Employee data self service non media
    """,

    'author': "MNC Group",
    'website': "http://www.mncgroup.com",
    'category': 'Human Resources',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','mnc_leave_management'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/hr_employee_security.xml',
        'views/hr_employee_views.xml',
        'views/hr_employee_menu.xml',
        'views/hr_grade_views.xml',
        'views/hr_level_views.xml',

    ],

}
