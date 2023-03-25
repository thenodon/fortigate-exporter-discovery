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
import argparse

from fmg_discovery.file_service_discovery import file_service_discovery
from fmg_discovery.http_service_discovery import http_service_discovery


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Prometheus Fortigate service discovery')
    parser.add_argument('--server', action='store_true',
                        help='Start in http service discovery mode',
                        dest='server')
    args = vars(parser.parse_args())

    if not args['server']:
        file_service_discovery()
    else:
        http_service_discovery()
