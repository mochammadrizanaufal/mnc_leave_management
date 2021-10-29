# -*- coding: utf-8 -*-
{
    'name': "MNC Time Off Management",

    'summary': """
        HRIS MNC""",

    'description': """
    """,

    'author': "MNC KAPITAL",
    'website': "http://www.mncgroup.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'hr_holidays'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/hr_timeoff_menu.xml',
        'views/hr_timeoff.xml',
        'views/hr_timeoff_allocation.xml',
        'views/hr_timeoff_type.xml',
        'views/hr_timeoff_policy.xml',
        # 'data/data.xml',
        'security/timeoff_security.xml',
        # 'data/ir_config_parameter.xml',
        # 'report/leave_form.xml'
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
}
