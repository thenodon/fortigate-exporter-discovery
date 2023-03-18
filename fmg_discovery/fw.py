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

from typing import Dict, Any


class Fortigate:
    def __init__(self, name: str, ip: str):
        self.name: str = name
        self.ip: str = ip
        self.token: str = ''
        self.port: int = 8443
        self.labels: Dict[str, str] = {}
        self.profile: str = ''

    def as_labels(self) -> Dict[str, str]:

        labels = self.labels.copy()
        if self.token:
            labels['token'] = self.token
        if self.profile:
            labels['profile'] = self.profile
        return labels

    def as_prometheus_file_sd_entry(self) -> Dict[str, Any]:
        return {'targets': [f"https://{self.ip}:{self.port}"], 'labels': self.as_labels()}
