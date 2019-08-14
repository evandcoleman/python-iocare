import json
import logging
import requests
import time
import collections
import base64
import binascii
from datetime import datetime
from urllib.parse import parse_qs, urlparse, quote
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto import Random
from Crypto.Util import Counter

from iocare.devices.purifier import Purifier

BASE_URI = 'https://iocareapp.coway.com/bizmob.iocare'
OAUTH_URL = "https://idp.coway.com/oauth2/v1/authorize"
SIGNIN_URL = "https://idp.coway.com/user/signin/"
REDIRECT_URL = "https://iocareapp.coway.com/bizmob.iocare/redirect/redirect.html"
CLIENT_ID = "UmVuZXdhbCBBcHA"
SERVICE_CODE = "com.coway.IOCareKor"
COWAY_ACCESS_TOKEN = "coway_access_token"
COWAY_REFRESH_TOKEN = "coway_refresh_token"
USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1"

DEVICE_LIST = 'CWIG0304'
TOKEN_REFRESH = 'CWIL0100'
STATUS = 'CWIG0602'
CONTROL = 'CWIG0603'
FILTERS = 'CWIA0120'

BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)

REFRESHTIME = 60 * 60 * 12
_LOGGER = logging.getLogger(__name__)

class IOCareSession:

    username = ''
    password = ''
    access_token = ''
    refresh_token = ''
    devices = []

SESSION = IOCareSession()

class IOCareApi:

    def __init__(self, username, password):
        SESSION.username = username
        SESSION.password = password

        if username is None or password is None:
            return None
        else:
            self.login()
            self.discover_devices()

    def devices(self):
        return SESSION.devices

    def login(self):
        state_id = self._get_state_id()
        cookies = self._authenticate(state_id)
        code = self._get_auth_code(cookies)
        access_token, refresh_token = self._get_token(code)
        SESSION.access_token = access_token
        SESSION.refresh_token = refresh_token

    def _get_state_id(self):
        response = requests.get(
            OAUTH_URL,
            headers= {
                'User-Agent': USER_AGENT
            },
            params= {
                'auth_type': 0,
                'response_type': 'code',
                'client_id': CLIENT_ID,
                'scope': 'login',
                'lang': 'en_US',
                'redirect_url': REDIRECT_URL
            },
        )
        return parse_qs(urlparse(response.url).query)['state'][0]

    def _authenticate(self, state_id):
        key = Random.new().read(16)
        iv = Random.new().read(AES.block_size)
        aes = AES.new(key, AES.MODE_CBC, IV=iv)
        i = base64.b64encode(iv).decode('utf-8')
        k = base64.b64encode(key).decode('utf-8')
        enc = aes.encrypt(pad(SESSION.password).encode('utf-8')).hex()
        response = requests.post(
            SIGNIN_URL,
            headers= {
                'Content-Type': 'application/json',
                'User-Agent': USER_AGENT
            },
            data= json.dumps({
                'username': SESSION.username,
                'password': i + ":" + enc + ":" + k,
                'state': state_id,
                'auto_login': 'Y'
            }),
        )
        return response.cookies

    def _get_auth_code(self, cookies):
        response = requests.get(
            OAUTH_URL,
            cookies= cookies,
            headers= {
                'User-Agent': USER_AGENT
            },
            params= {
                'auth_type': 0,
                'response_type': 'code',
                'client_id': CLIENT_ID,
                'scope': 'login',
                'lang': 'en_US',
                'redirect_url': REDIRECT_URL
            },
        )
        return parse_qs(urlparse(response.url).query)['code'][0]

    def _get_token(self, code):
        response = self._request(TOKEN_REFRESH, {
            'authCode': code,
            'isMobile': 'M',
            'langCd': 'en',
            'osType': 1,
            'redirectUrl': REDIRECT_URL,
            'serviceCode': SERVICE_CODE  
        })
        json = response.json()
        return (json['header']['accessToken'], json['header']['refreshToken'])

    def _refresh_token(self):
        response = self._request(TOKEN_REFRESH, {
            'isMobile': 'M',
            'langCd': 'en',
            'osType': 1,
            'redirectUrl': REDIRECT_URL,
            'serviceCode': SERVICE_CODE  
        })
        json = response.json()
        SESSION.access_token = json['header']['accessToken']
        SESSION.refresh_token = json['header']['refreshToken']

    def discover_devices(self):
        response = self._request(DEVICE_LIST, {
            'pageIndex': '0',
            'pageSize': '100'
        })
        device_infos = response.json()['body']['deviceInfos']
        devices = []
        for device in device_infos:
            devices.append(Purifier(device, self))
        SESSION.devices = devices

    def refresh_devices(self):
        for device in SESSION.devices:
            device.refresh()

    def control_status(self, device):
        response = self._request(STATUS, {
            'barcode': device.device_id,
            'dvcBrandCd': device.device_brand,
            'prodName': device.product_name,
            'stationCd': '',
            'resetDttm': '',
            'dvcTypeCd': device.device_type,
            'refreshFlag': 'true'
        })
        return response.json()['body']['controlStatus']

    def quality_status(self, device):
        response = self._request(FILTERS, {
            'barcode': device.device_id,
            'dvcBrandCd': device.device_brand,
            'prodName': device.product_name,
            'stationCd': '',
            'resetDttm': '',
            'dvcTypeCd': device.device_type,
            'refreshFlag': 'true'
        })
        body = response.json()['body']
        return (body['filterList'], body['prodStatus'], body['IAQ'])

    def control(self, device, command, value):
        response = self._request(CONTROL, {
            'barcode': device.device_id,
            'dvcBrandCd': device.device_brand,
            'prodName': device.product_name,
            'dvcTypeCd': device.device_type,
            'funcList': [{
              'comdVal': value,
              'funcId': command
            }]
        })

    def _request(self, endpoint, params):
        message = {
            'header': {
                'trcode': endpoint,
                'accessToken': SESSION.access_token,
                'refreshToken': SESSION.refresh_token
            },
            'body': params
        }
        return requests.post(
            BASE_URI + '/' + endpoint + '.json',
            headers= {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
                'User-Agent': USER_AGENT
            },
            data= {
                'message': json.dumps(message)
            },
        )

    def check_access_token(self):
        if SESSION.username == '' or SESSION.password == '':
            raise IOCareAPIException("can not find username or password")
            return
        if SESSION.access_token == '' or SESSION.refresh_token == '':
            self.login()

    def poll_devices_update(self):
        self.check_access_token()
        self.refresh_devices()

    def get_all_devices(self):
        return SESSION.devices

    def get_device_by_id(self, dev_id):
        for device in SESSION.devices:
            if device.device_id() == dev_id:
                return device
        return None


class IOCareAPIException(Exception):
    pass
