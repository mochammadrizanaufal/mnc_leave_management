from odoo import http, api
from odoo.http import request
import logging
import json

_logger = logging.getLogger(__name__)


class HRISController(http.Controller):

    @http.route(['/api/hris_mnc/leave_approval'], type='json', auth='none', csrf=False, methods=['POST'])
    def approve_leave_request(self, **kwargs):
        if request.httprequest.method == 'POST':
            data = kwargs.get('data', '')
            approval_value, leave_request_id = data.split('|')
            env = api.Environment(request.cr, 1, request.context)
            leave_obj = env['hr.leave'].browse(int(leave_request_id))
            if str(approval_value).strip().lower() == 't':
                if leave_obj.state == 'confirm':
                    leave_obj.action_approve()
                elif leave_obj.state == 'validate1':
                    leave_obj.action_validate()
            else:
                leave_obj.action_refuse()
            return {'status': 'ok'}
        return {'status': 'failed'}