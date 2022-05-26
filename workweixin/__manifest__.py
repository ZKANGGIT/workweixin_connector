# -*- coding: utf-8 -*-
{
    'name': "workweixin",
    'summary': """Enterprise wechat connector""",
    'description': """Enterprise wechat connector""",
    'author': "My Company",
    'category': 'connector/workweixin',
    'version': '0.1',
    'depends': ['base'],
    'data': [
        'security/workweixin_security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/web_login.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
