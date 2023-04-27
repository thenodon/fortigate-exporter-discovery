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

from typing import Dict, List, Any, Tuple
import ipaddress


class Fortigate:
    def __init__(self, name: str, ip: str):
        self.name: str = name.strip()
        self.ip: str = ip.strip()
        self.token: str = ''
        self.port: int = 443
        self.adom: str = ''
        self.latitude: str = ''
        self.longitude: str = ''
        self.platform: str = ''
        self.labels: Dict[str, str] = {'name': self.name}
        self.profile: str = ''

        self.conf_status: str = ''
        self.conn_mode: str = ''
        self.conn_status: str = ''
        self.desc: str = ''
        self.ha_group_id: str = ''
        self.ha_group_name: str = ''
        self.ha_mode: str = ''
        self.ha_slave: List[Dict[str, Any]] = []

    def _as_labels(self) -> Dict[str, str]:

        labels = self.labels.copy()
        labels['adom'] = self.adom
        labels['latitude'] = self.latitude
        labels['longitude'] = self.longitude
        labels['platform'] = self.platform

        if self.token:
            labels['token'] = self.token
        if self.profile:
            labels['profile'] = self.profile

        return labels

    def valid(self) -> Tuple[bool, str]:
        valid = True
        cause = ""
        if not self.name:
            cause = f"Missing name {cause}"
            valid = False
        if not self.ip:
            cause = f"Missing ip {cause}"
            valid = False
        if self.ip and not ipaddress.ip_address(self.ip):
            cause = f"Not a ip4/ip6 address {cause}"
            valid = False
        if not self.token:
            cause = f"Missing token {cause}"
            valid = False

        return valid, cause

    def as_prometheus_file_sd_entry(self) -> Dict[str, Any]:
        return {'targets': [f"https://{self.ip}:{self.port}"], 'labels': self._as_labels()}


def fw_factory(adom, device) -> Fortigate:
    fw = Fortigate(name=device['name'], ip=device['ip'])
    # Discovery
    fw.latitude = device['latitude'].strip()
    fw.longitude = device['longitude'].strip()
    fw.platform = device['platform_str'].strip()

    if 'labels' in adom:
        fw.labels.update(adom['labels'])
    if 'token' in adom['fortigate']:
        fw.token = adom['fortigate']['token']
    if 'port' in adom['fortigate']:
        fw.port = adom['fortigate']['port']
    if 'profile' in adom['fortigate']:
        fw.profile = adom['fortigate']['profile']

    fw.conf_status = device['conf_status'].strip()
    fw.conn_mode = device['conn_mode'].strip()
    fw.conn_status = device['conn_status'].strip()
    fw.desc = device['desc'].strip()
    fw.ha_group_id = str(device['ha_group_id']).strip()
    fw.ha_group_name = device['ha_group_name'].strip()
    fw.ha_mode = device['ha_mode'].strip()
    if device['ha_slave'] and isinstance(device['ha_slave'], list):
        fw.ha_slave.extend(device['ha_slave'])

    return fw
