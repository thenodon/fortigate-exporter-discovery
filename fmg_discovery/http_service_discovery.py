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

import secrets
import json
import os
import sys
from typing import List, Any, Annotated

import uvicorn
import yaml

from fastapi import FastAPI, Response, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

import logging.config as lc

from fmg_discovery.environments import FMG_DISCOVERY_CONFIG
from fmg_discovery.fmg_api import FMG
from fmg_discovery.fmglogging import Log
from fmg_discovery.environments import FMG_DISCOVERY_BASIC_AUTH_USERNAME, FMG_DISCOVERY_BASIC_AUTH_PASSWORD, \
    FMG_DISCOVERY_BASIC_AUTH_ENABLED, FMG_DISCOVERY_LOG_LEVEL, FMG_DISCOVERY_HOST, FMG_DISCOVERY_PORT

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

security = HTTPBasic()


def basic_auth(credentials: Annotated[HTTPBasicCredentials, Depends(security)]) -> bool:
    if not os.getenv(FMG_DISCOVERY_BASIC_AUTH_ENABLED):
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


@app.get('/')
def hello_world():
    return Response("fmg_discovery alive!", status_code=status.HTTP_200_OK, media_type=MIME_TYPE_TEXT_HTML)


@app.get('/prometheus-sd-targets')
def discovery(auth: Annotated[str, Depends(basic_auth)]):

    fmg = FMG(Config().get())
    fws = fmg.get_fmg_devices()

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
