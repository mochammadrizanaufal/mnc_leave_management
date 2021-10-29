
from time import sleep
import requests
import json
token_bot = '1784447130:AAHA3BFLK3izFbsFUb4qpD7RuLiAxSrKT5k'
url = 'https://api.telegram.org/bot{token}'.format(token=token_bot)
odoo_api_url = 'http://localhost:8069/api/hris_mnc/leave_approval'


def process_command(chat_id, command):
    print('data = %s' % command)
    data = {'chat_id': chat_id, 'text': 'Sent'}
    resp = requests.post(url + '/sendMessage', json=data)
    headers = {
        'content-type': 'application/json',
        'accept': 'application/json',
    }
    resp = requests.post(url=odoo_api_url, headers=headers, data=json.dumps({'params': {'data': command}}))
    print(resp.json())


if __name__ == '__main__':
    last_update_id = 0
    while True:
        resp = requests.get(url + '/getUpdates?offset=%s' % last_update_id).json()
        if resp.get('result'):
            result = resp['result'][-1]
            print(result)
            last_update_id = result.get('update_id', '')
            if isinstance(last_update_id, int):
                last_update_id += 1
                callback_query = result.get('callback_query', {})
                process_command(callback_query.get('from', {}).get('id'), callback_query.get('data'))
        sleep(5)