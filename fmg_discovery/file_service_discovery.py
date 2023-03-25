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
import os
from typing import List, Dict, Any

import yaml

from fmg_discovery.environments import FMG_DISCOVERY_PROMETHEUS_SD_FILE_DIRECTORY, FMG_DISCOVERY_CONFIG
from fmg_discovery.fmg_api import FMG


def file_service_discovery():
    # Run for as file service discovery
    if not os.getenv(FMG_DISCOVERY_PROMETHEUS_SD_FILE_DIRECTORY):
        print(f"Env FMG_PROMETHEUS_SD_FILE_DIRECTORY must be set to a existing directory path")
        exit(1)
    if not os.path.exists(os.getenv(FMG_DISCOVERY_PROMETHEUS_SD_FILE_DIRECTORY)):
        print(f"Directory {FMG_DISCOVERY_PROMETHEUS_SD_FILE_DIRECTORY} does not exists")
        exit(1)
    with open(os.getenv(FMG_DISCOVERY_CONFIG, 'config.yml'), 'r') as config_file:
        try:
            # Converts yaml document to python object
            config = yaml.safe_load(config_file)

        except yaml.YAMLError as err:
            print(err)

    fmg = FMG(config)
    fws = fmg.get_fmg_devices()

    prometheus_file_sd: Dict[str, List[Any]] = {}
    for adom_name, fws in fws.items():
        for fw in fws:

            if adom_name not in prometheus_file_sd:
                prometheus_file_sd[adom_name] = []
            prometheus_file_sd[adom_name].append(fw.as_prometheus_file_sd_entry())

        # Generate configuration
        with open(f"{os.getenv(FMG_DISCOVERY_PROMETHEUS_SD_FILE_DIRECTORY)}/{adom_name}.yaml", 'w') as config_file:
            try:
                yaml.safe_dump(prometheus_file_sd[adom_name], config_file)
            except yaml.YAMLError as err:
                print(err)
