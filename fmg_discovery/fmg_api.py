# -*- coding: utf-8 -*-
"""
    Copyright (C) 2023  Anders Håål

    This file is part of fortigate-exporter-discovery.

    fortigate-exporter-discovery is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    fortigate-exporter-discovery is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with fortigate-exporter-discovery.  If not, see <http://www.gnu.org/licenses/>.

"""

import json

from typing import List, Dict, Any

import requests
import urllib3
import logging
from fmg_discovery.fw import Fortigate

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger(__name__)


class FMG:
    def __init__(self, config):
        """
        Init
        :param credentials: a dict {'host': 'localhost:3443', 'username': 'abc', 'password': 'XYZ'}
        :param customer_conf: a dict {'fmg': {'adoms': ["SDWAN_Adoms"]}}
        """
        self.credentials = {'host': config.get('fmg').get('host'), 'username': config.get('fmg').get('username'),
                            'password': config.get('fmg').get('password')}
        self.fmg_configuration = config
        self.request_url = self.credentials['host'] + "/jsonrpc"
        self.session = None

    def _fmg_login(self):
        """
        Login at create a session
        :return:
        """

        datagram = {"id": 1, "method": "exec", "params": [
            {"data": {"passwd": self.credentials["password"], "user": self.credentials["username"]},
             "url": "/sys/login/user"}]}
        try:
            response_raw = requests.post(self.request_url, data=json.dumps(datagram),
                                         headers={'content-type': 'application/json'}, verify=False, timeout=10)
            response_login = response_raw.json()
            assert response_login['id'] == datagram['id']
            self.session = response_login["session"]

        except requests.exceptions.ConnectionError as err:
            log.error(f"Connection error on login: {err}")
        except Exception as err:
            log.error(f"Error on login: {err}")

    def get_fmg_devices(self) -> Dict[str, List[Fortigate]]:
        """
        Get FW data from FMG
        """

        if self.session is None:
            self._fmg_login()
        # Get all Firewalls in this ADOM
        if not self.fmg_configuration['fmg']['adoms']:
            log.warning(f"ADOM is not configured. No data received from FortiManager.")
            return {}
        # Loop for each adom
        all_adom_devices = {}
        for adom in self.fmg_configuration['fmg']['adoms']:
            all_devices = []
            devices = self._get_fw_devices(adom['name'])
            for device in devices:
                fw = Fortigate(name=device['name'], ip=device['ip'])
                fw.labels['adom'] = adom['name']
                fw.labels['latitude'] = device['latitude']
                fw.labels['longitude'] = device['longitude']
                fw.labels['platform'] = device['platform_str']

                if 'labels' in adom:
                    fw.labels.update(adom['labels'])
                if 'token' in adom['fortigate']:
                    fw.token = adom['fortigate']['token']
                if 'port' in adom['fortigate']:
                    fw.port = adom['fortigate']['port']
                if 'profile' in adom['fortigate']:
                    fw.profile = adom['fortigate']['profile']
                all_devices.append(fw)
            all_adom_devices[adom['name']] = all_devices

        return all_adom_devices

    def get_adoms(self) -> List[str]:
        """
        Get all adoms data from FMG
        """

        if self.session is None:
            self._fmg_login()
        # Get all Firewalls in this ADOM
        # Loop for each adom

        filtered_adoms = []
        adoms = self._get_adoms()
        for adom in adoms:
            if 'mr' in adom and adom['mr'] == '4':
                filtered_adoms.append(adom)
        return filtered_adoms

    def _get_adoms(self) -> List[str]:
        # Data fields to collect from fmg
        url = "/dvmdb/adom"
        datagram = {"id": 1, "method": "get", "params": [{"url": url}], "session": self.session,
                    "verbose": 1}
        # To get all parameters -
        # datagram = {"id": 1, "method": "get", "params": [{"url": url}], "session": self.session}
        # Get data about Adom devices
        adoms = []
        try:
            response_raw = requests.post(self.request_url, data=json.dumps(datagram),
                                         headers={'content-type': 'application/json'}, verify=False, timeout=10)
            response_data = response_raw.json()
            if response_data["result"][0]["status"]["code"] != 0:
                log.error(f"Data from API {str(response_data['result'][0]['url'])} "
                          f"returned code: {str(response_data['result'][0]['status']['code'])} "
                          f"with message: {str(response_data['result'][0]['status']['message'])}")
            else:
                adoms = response_data["result"][0]["data"]
                log.info(f"Total adoms - found {len(adoms)}")
            return adoms
        except requests.exceptions.ConnectionError as err:
            log.error(f"Connection Error on data retrieval: {err}")
        except Exception as err:
            log.error(f"Error on data retrieval: {err}")

    def _get_fw_devices(self, adom) -> List[Dict[str, Any]]:
        # Data fields to collect from fmg
        fields = ["name", "hostname", "alias", "ip", "sn", "hostname", "latitude", "longitude", "tunnel_ip", "os_ver",
                  "mr", "build", "patch", "ha_mode", "ha_slave", "ha_group_id", "ha_group_name", "hw_rev_major",
                  "conf_status", "conn_status", "conn_mode", "desc", "mgmt_if", "mgmt_mode", "platform_str"]
        url = "/dvmdb/adom/" + adom + "/device"
        datagram = {"id": 1, "method": "get", "params": [{"url": url, "fields": fields}], "session": self.session,
                    "verbose": 1}
        # To get all parameters -
        # datagram = {"id": 1, "method": "get", "params": [{"url": url}], "session": self.session}
        # Get data about Adom devices
        devices = []
        try:
            response_raw = requests.post(self.request_url, data=json.dumps(datagram),
                                         headers={'content-type': 'application/json'}, verify=False, timeout=10)
            response_data = response_raw.json()
            if response_data["result"][0]["status"]["code"] != 0:
                log.error(f"Data from API {str(response_data['result'][0]['url'])} "
                          f"returned code: {str(response_data['result'][0]['status']['code'])} "
                          f"with message: {str(response_data['result'][0]['status']['message'])}")
            else:
                devices = response_data["result"][0]["data"]
                log.info(f"{adom} - found {len(devices)} firewalls.")
            return devices
        except requests.exceptions.ConnectionError as err:
            log.error(f"Connection Error on data retrieval: {err}")
        except Exception as err:
            log.error(f"Error on data retrieval: {err}")
