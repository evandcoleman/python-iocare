import json
import logging
import requests
import time
import collections
from datetime import datetime

from bondpy.devices.factory import get_bond_device


BONDAPIBASE = "https://appbond.com/api/v1"

REFRESHTIME = 60 * 60 * 12

_LOGGER = logging.getLogger(__name__)


class BondSession:

    email = ''
    password = ''
    host = None
    key = ''
    token = ''
    devices = []


SESSION = BondSession()


class BondApi:

    def __init__(self, email, password, host):
        SESSION.email = email
        SESSION.password = password
        SESSION.host
        self.seq = 0

        if email is None or password is None:
            return None
        else:
            self.get_access_token()
            self.discover_devices()

    def devices(self):
        return SESSION.devices

    def get_access_token(self):
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.post(
            (BONDAPIBASE+'/auth/login/'),
            headers= headers,
            data= json.dumps({'email': SESSION.email, 'password': SESSION.password}),
        )
        response_json = response.json()

        SESSION.key = response_json.get('key')
        SESSION.token = response_json.get('user').get('bond_token')

    def check_access_token(self):
        if SESSION.email == '' or SESSION.password == '':
            raise BondAPIException("can not find email or password")
            return
        if SESSION.key == '' or SESSION.token == '':
            self.get_access_token()

    def poll_devices_update(self):
        self.check_access_token()
        return self.discover_devices()

    def discover_devices(self):
        response = requests.get('https://appbond.com/api/v1/bonds/', headers={'Authorization': 'Token ' + SESSION.key}).json()
        SESSION.devices = []
        SESSION.bondId = response['results'][0]['id']

        result = collections.defaultdict(list)
        for d in response['results'][0]['commands']:
            result[d['device_property_id']].append(d)
        device_list = result.values()

        for device in device_list:
            SESSION.devices.extend(get_bond_device(device, self))
        return device_list

    def get_devices_by_type(self, dev_type):
        device_list = []
        for device in SESSION.devices:
            if device.dev_type() == dev_type:
                device_list.append(device)

    def get_all_devices(self):
        return SESSION.devices

    def get_device_by_id(self, dev_id):
        for device in SESSION.devices:
            if device.object_id() == dev_id:
                return device
        return None

    def device_control(self, devId, commandId):
        self.seq += 1
        if SESSION.host is None:
            url = "https://" + SESSION.bondId + ":4433/api/v1/device/" + str(int(devId) - 1) + "/device_property/" + devId + "/device_property_command/" + commandId + "/run"
        else:
            url = "https://" + SESSION.host + ":4433/api/v1/device/" + str(int(devId) - 1) + "/device_property/" + devId + "/device_property_command/" + commandId + "/run"
        headers = {'X-Token': SESSION.token, 'X-Sequence': str(self.seq), 'X-BondDate': datetime.utcnow().isoformat().split('.')[0] + 'Z'}
        requests.get(url, headers=headers, verify=False)


class BondAPIException(Exception):
    pass
