from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import requests

from aisysprojserver.active_env_management import MakeEnvRequest

logger = logging.getLogger(__name__)


class AdminClient:
    def __init__(self, url: str, password: str):
        self.base_url = url
        self.pwd = password

    @classmethod
    def from_file(cls, path: Path) -> AdminClient:
        with open(path) as fp:
            data = json.load(fp)
            return AdminClient(data['url'], data['password'])

    def send_request(self, path: str, **kwargs) -> tuple[int, Any]:
        """ Overwritten for integration tests """
        response = requests.request(url=self.base_url + path, **kwargs)
        response_log_level: int = logging.DEBUG
        if response.status_code not in {200, 201}:
            response_log_level = logging.ERROR
        logger.log(response_log_level, f'Got a {response.status_code} response with content: {response.text}')
        return response.status_code, response.json()

    def new_user(self, env: str, user: str, overwrite: bool = False) -> tuple[int, Any]:
        return self.send_request(f'makeagent/{env}/{user}', method='POST', json={
            'overwrite': overwrite,
            'admin-pwd': self.pwd,
        })

    def make_env(self, env_class: str, identifier: str, display_name: str, config: str = False,
                 overwrite: bool = False) -> tuple[int, Any]:
        data = MakeEnvRequest(env_class=env_class, display_name=display_name, config=config, overwrite=overwrite).to_dict()
        data['admin-pwd'] = self.pwd
        return self.send_request(f'makeenv/{identifier}', method='PUT', json=data)

# class MakeEnvRequest:
#     env_class: str
#     display_name: str
#     settings: str = ''
#     overwrite: bool = False
