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

from typing import Dict, List

from prometheus_client.core import GaugeMetricFamily
from prometheus_client.metrics_core import Metric

from fmg_discovery.fmglogging import Log
from fmg_discovery.fw import Fortigate
from fmg_discovery.transform import Transform, LabelsBase

# Constants to map response data
SYSTEM_INFO_TIME = 'system_info_time'
SYSTEM_INFO_USAGE = 'system_info_usage'
SYSTEM_INFO = 'system_info'
VPN_TUNNELS = 'vpn_tunnels'

log = Log(__name__)


class FmgMetricDefinition:
    prefix = 'fmg_'
    help_prefix = ''

    class Labels(LabelsBase):
        def __init__(self):
            super().__init__()
            self.labels = {'ip': "", 'name': "", 'adom': "", 'platform': ''}

    @staticmethod
    def metrics_definition() -> Dict[str, Metric]:
        common_labels = FmgMetricDefinition.Labels().get_label_keys()

        metric_definition = {
            "conf_status":
                GaugeMetricFamily(name=f"{FmgMetricDefinition.prefix}conf_status",
                                  documentation=f"{FmgMetricDefinition.help_prefix}Configuration status 1==insync "
                                                f"0==all other states",
                                  labels=common_labels),
            "conn_status":
                GaugeMetricFamily(name=f"{FmgMetricDefinition.prefix}conn_status",
                                  documentation=f"{FmgMetricDefinition.help_prefix}Connection status 1==up "
                                                f"0==all other states",
                                  labels=common_labels),
            "conn_mode":
                GaugeMetricFamily(name=f"{FmgMetricDefinition.prefix}conn_mode",
                                  documentation=f"{FmgMetricDefinition.help_prefix}Connection mode 1==active "
                                                f"0==all other states",
                                  labels=common_labels),
        }

        return metric_definition


class FmgMetric(FmgMetricDefinition.Labels):
    def __init__(self):
        super().__init__()
        self.conf_status: float = 0
        self.conn_status: float = 0
        self.conn_mode: float = 0


class FmgMetrics(Transform):

    def __init__(self, fws: Dict[str, List[Fortigate]]):
        self.fws = fws
        self.all_metrics: List[FmgMetric] = []

    def metrics(self):

        metrics_list = FmgMetricDefinition.metrics_definition()
        for attribute in metrics_list.keys():
            for m in self.all_metrics:
                metrics_list[attribute].add_metric(m.get_label_values(),
                                                   m.__dict__.get(attribute))

        for m in metrics_list.values():
            yield m

    def parse(self):

        for adom, fw in self.fws.items():
            for f in fw:
                metric = FmgMetric()

                metric.conf_status = FmgMetrics.status_mapping(f.conf_status, "insync")
                metric.conn_status = FmgMetrics.status_mapping(f.conn_status, "up")
                metric.conn_mode = FmgMetrics.status_mapping(f.conn_mode, "active")

                metric.add_label('ip', f.ip)
                metric.add_label('adom', f.adom)
                metric.add_label('name', f.name)
                metric.add_label('platform', f.platform)
                self.all_metrics.append(metric)

    @staticmethod
    def status_mapping(status: str, valid: str) -> float:
        if status == valid:
            return 1.0
        return 0.0
