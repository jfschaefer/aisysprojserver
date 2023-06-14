from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

import requests

from aisysprojserver.active_env_management import MakeEnvRequest

logger = logging.getLogger(__name__)


class AdminClient:
    def __init__(self, url: str, password: Optional[str] = None):
        if not url.endswith('/'):
            url += '/'
        self.base_url = url
        if password is None:
            with open(Path('~/.aisysprojserver_auth').expanduser(), 'r') as fp:
                password = fp.read().strip()
        self.pwd: str = password

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
        code, content = self.send_request(f'makeagent/{env}/{user}', method='POST', json={
            'overwrite': overwrite,
            'admin-pwd': self.pwd,
        })
        if code == 200:
            content['url'] = self.base_url
        return code, content

    def make_env(self, env_class: str, identifier: str, display_name: str, display_group: str, config: Any = {},
                 overwrite: bool = False) -> tuple[int, Any]:
        data = MakeEnvRequest(env_class=env_class, display_name=display_name, display_group=display_group,
                              config=config, overwrite=overwrite).to_dict()
        data['admin-pwd'] = self.pwd
        return self.send_request(f'makeenv/{identifier}', method='PUT', json=data)

    def print_errors(self):
        code, errors = self.send_request('errors', method='GET', json={'admin-pwd': self.pwd})
        assert code == 200
        for error in errors:
            print('---------------ERROR--------------------')
            print(error)

    def print_diskusage(self):
        code, content = self.send_request('diskusage', method='GET', json={'admin-pwd': self.pwd})
        assert code == 200
        print(content)

    def get_agent_results(self, env: str):
        code, content = self.send_request(f'results/{env}', method='GET')
        assert code == 200
        return content
