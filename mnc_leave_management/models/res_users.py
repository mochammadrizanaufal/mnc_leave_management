from odoo import api, fields, models


class User(models.Model):
    _inherit = "res.users"

    telegram_chat_id = fields.Char('Telegram Chat ID')
    esignature = fields.Binary(
            string='e-Signature',
            attachment=True,
            help="This field holds the image for e-signature document",
            groups='base.group_user'
        )
