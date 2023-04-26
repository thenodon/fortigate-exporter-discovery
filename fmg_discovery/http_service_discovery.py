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

    The following functions are from the project https://github.com/prometheus/client_python and under license
    https://github.com/prometheus/client_python/blob/master/LICENSE. The reason they are copied is due to the async
    implementation in the fortigate_exporter
    - floatToGoString
    - generate_latest

"""
import json
import logging.config as lc
import math
import os
import secrets
import sys
import time
from typing import List, Any, Annotated, Dict

import uvicorn
import yaml
from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from prometheus_client import CollectorRegistry, Gauge
from prometheus_client.exposition import CONTENT_TYPE_LATEST
from prometheus_client.utils import INF, MINUS_INF
from prometheus_fastapi_instrumentator import Instrumentator

from fmg_discovery.environments import FMG_DISCOVERY_BASIC_AUTH_USERNAME, FMG_DISCOVERY_BASIC_AUTH_PASSWORD, \
    FMG_DISCOVERY_BASIC_AUTH_ENABLED, FMG_DISCOVERY_LOG_LEVEL, FMG_DISCOVERY_HOST, FMG_DISCOVERY_PORT, \
    FMG_DISCOVERY_CACHE_TTL

from fmg_discovery.environments import FMG_DISCOVERY_CONFIG
from fmg_discovery.exceptions import FmgException
from fmg_discovery.fmg_api import FMG
from fmg_discovery.fmg_collector import FmgCollector
from fmg_discovery.fmglogging import Log
from fmg_discovery.fw import Fortigate

FORMAT = 'timestamp="%(asctime)s" level=%(levelname)s module="%(module)s" %(message)s'
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
lc.dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': FORMAT,
        'datefmt': TIME_FORMAT
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://sys.stdout',
        'formatter': 'default'
    }},
    'root': {
        'level': os.getenv(FMG_DISCOVERY_LOG_LEVEL, 'WARNING'),
        'handlers': ['wsgi']
    }
})

MIME_TYPE_TEXT_HTML = 'text/html'
MIME_TYPE_APPLICATION_JSON = 'application/json'
log = Log(__name__)

app = FastAPI()

# Enable auto instrumentation
Instrumentator().instrument(app).expose(app=app, endpoint="/exporter-metrics")

security = HTTPBasic()


async def optional_security(request: Request):
    if os.getenv(FMG_DISCOVERY_BASIC_AUTH_ENABLED) and os.getenv(FMG_DISCOVERY_BASIC_AUTH_ENABLED) == "true":
        return await security(request)
    else:
        return None


async def basic_auth(credentials: Annotated[HTTPBasicCredentials, Depends(optional_security)]) -> bool:
    if not os.getenv(FMG_DISCOVERY_BASIC_AUTH_ENABLED) or os.getenv(FMG_DISCOVERY_BASIC_AUTH_ENABLED) == "false":
        return True

    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = bytes(os.getenv(FMG_DISCOVERY_BASIC_AUTH_USERNAME), 'utf-8')
    is_correct_username = secrets.compare_digest(
        current_username_bytes, correct_username_bytes
    )
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = bytes(os.getenv(FMG_DISCOVERY_BASIC_AUTH_PASSWORD), 'utf-8')
    is_correct_password = secrets.compare_digest(
        current_password_bytes, correct_password_bytes
    )
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Config(metaclass=Singleton):

    def __init__(self):
        self.config = {}
        with open(os.getenv(FMG_DISCOVERY_CONFIG, 'config.yml'), 'r') as config_file:
            try:
                self.config = yaml.safe_load(config_file)
            except yaml.YAMLError as err:
                log.error(err)
                sys.exit(1)

    def get(self):
        return self.config


class Cache(metaclass=Singleton):

    def __init__(self):
        self._ttl: int = int(os.getenv(FMG_DISCOVERY_CACHE_TTL, "60"))
        self._expire: int = 0
        self._cache: Dict[str, Any] = {}

    def put(self, data: Dict[str, List[Fortigate]]):
        self._expire = time.time() + self._ttl
        self._cache = data

    def get(self) -> Dict[str, List[Fortigate]]:
        if time.time() < self._expire:
            log.info_fmt({"operation": "cache", "hit": True})
            return self._cache
        log.info_fmt({"operation": "cache", "hit": False})
        return {}


def floatToGoString(d):
    d = float(d)
    if d == INF:
        return '+Inf'
    elif d == MINUS_INF:
        return '-Inf'
    elif math.isnan(d):
        return 'NaN'
    else:
        s = repr(d)
        dot = s.find('.')
        # Go switches to exponents sooner than Python.
        # We only need to care about positive values for le/quantile.
        if d > 0 and dot > 6:
            mantissa = '{0}.{1}{2}'.format(s[0], s[1:dot], s[dot + 1:]).rstrip('0.')
            return '{0}e+0{1}'.format(mantissa, dot - 1)
        return s


def generate_latest(metrics_list: list):
    """
    Returns the metrics from the registry in text format as a string
    :param metrics_list:
    :return:
    """
    """"""

    def sample_line(line):
        if line.labels:
            labelstr = '{{{0}}}'.format(','.join(
                ['{0}="{1}"'.format(
                    k, v.replace('\\', r'\\').replace('\n', r'\n').replace('"', r'\"'))
                    for k, v in sorted(line.labels.items())]))
        else:
            labelstr = ''
        timestamp = ''
        if line.timestamp is not None:
            # Convert to milliseconds.
            timestamp = ' {0:d}'.format(int(float(line.timestamp) * 1000))
        return '{0}{1} {2}{3}\n'.format(
            line.name, labelstr, floatToGoString(line.value), timestamp)

    output = []
    for metric in metrics_list:
        try:
            mname = metric.name
            mtype = metric.type
            # Munging from OpenMetrics into Prometheus format.
            if mtype == 'counter':
                mname = mname + '_total'
            elif mtype == 'info':
                mname = mname + '_info'
                mtype = 'gauge'
            elif mtype == 'stateset':
                mtype = 'gauge'
            elif mtype == 'gaugehistogram':
                # A gauge histogram is really a gauge,
                # but this captures the structure better.
                mtype = 'histogram'
            elif mtype == 'unknown':
                mtype = 'untyped'

            output.append('# HELP {0} {1}\n'.format(
                mname, metric.documentation.replace('\\', r'\\').replace('\n', r'\n')))
            output.append('# TYPE {0} {1}\n'.format(mname, mtype))

            om_samples = {}
            for s in metric.samples:
                for suffix in ['_created', '_gsum', '_gcount']:
                    if s.name == metric.name + suffix:
                        # OpenMetrics specific sample, put in a gauge at the end.
                        om_samples.setdefault(suffix, []).append(sample_line(s))
                        break
                else:
                    output.append(sample_line(s))
        except Exception as exception:
            exception.args = (exception.args or ('',)) + (metric,)
            raise

        for suffix, lines in sorted(om_samples.items()):
            output.append('# HELP {0}{1} {2}\n'.format(metric.name, suffix,
                                                       metric.documentation.replace('\\', r'\\').replace('\n', r'\n')))
            output.append('# TYPE {0}{1} gauge\n'.format(metric.name, suffix))
            output.extend(lines)
    return ''.join(output).encode('utf-8')


@app.get('/')
def alive(request: Request):
    request.app.state.users_events_counter.inc({"path": request.scope["path"]})
    return Response("fmg_discovery alive!", status_code=status.HTTP_200_OK, media_type=MIME_TYPE_TEXT_HTML)


@app.get('/metrics')
async def get_metrics():
    start_time = time.time()
    cache = Cache()
    fws = cache.get()
    if not fws:
        fmg = FMG(Config().get())
        fws = fmg.get_fmg_devices()
        cache.put(fws)

    registry = CollectorRegistry()
    try:
        fmg_collector = FmgCollector(fws)

        registry.register(fmg_collector)

        duration = Gauge('fmg_scrape_duration_seconds', 'Time spent processing request', registry=registry)

        duration.set(time.time() - start_time)

        fortigate_response = generate_latest(await fmg_collector.collect())

        duration.set(time.time() - start_time)
        return Response(fortigate_response, status_code=200, media_type=CONTENT_TYPE_LATEST)
    except FmgException as err:
        log.error(err.message)
        return Response(err.message, status_code=err.status, media_type=MIME_TYPE_TEXT_HTML)
    except Exception as err:
        log.error(f"Failed to create metrics - err: {str(err)}")
        return Response(f"Internal server error for - please check logs", status_code=500,
                        media_type=MIME_TYPE_TEXT_HTML)


@app.get('/prometheus-sd-targets')
def discovery(auth: Annotated[str, Depends(basic_auth)]):
    cache = Cache()
    fws = cache.get()
    if not fws:
        fmg = FMG(Config().get())
        fws = fmg.get_fmg_devices()
        cache.put(fws)

    prometheus_sd: List[Any] = []
    for adom_name, fws in fws.items():
        for fw in fws:
            prometheus_sd.append(fw.as_prometheus_file_sd_entry())

    targets = json.dumps(prometheus_sd, indent=4)
    return Response(targets, status_code=status.HTTP_200_OK, media_type=MIME_TYPE_APPLICATION_JSON)


def http_service_discovery():
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = FORMAT
    log_config["formatters"]["access"]['datefmt'] = TIME_FORMAT
    log_config["formatters"]["default"]["fmt"] = FORMAT
    log_config["formatters"]["default"]['datefmt'] = TIME_FORMAT
    log_config["loggers"]["uvicorn.access"]["level"] = os.getenv(FMG_DISCOVERY_LOG_LEVEL, 'WARNING')

    uvicorn.run(app, host=os.getenv(FMG_DISCOVERY_HOST, "0.0.0.0"), port=os.getenv(FMG_DISCOVERY_PORT, 9693),
                log_config=log_config)
