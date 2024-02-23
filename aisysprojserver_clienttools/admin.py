from __future__ import annotations

import base64
import io
import json
import logging
from pathlib import Path
from typing import Any, Optional
from zipfile import ZipFile

import requests

from aisysprojserver.active_env_management import MakeEnvRequest
from aisysprojserver.group_management import MakeGroupRequest

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

    def make_env(self, env_class: str, identifier: str, display_name: str, config: Any = {},
                 overwrite: bool = False) -> tuple[int, Any]:
        data = MakeEnvRequest(env_class=env_class, display_name=display_name,
                              config=config, overwrite=overwrite).to_dict()
        data['admin-pwd'] = self.pwd
        return self.send_request(f'makeenv/{identifier}', method='PUT', json=data)

    def make_group(self, identifier: str, title: str, description: str, overwrite: bool = False) -> tuple[int, Any]:
        data = MakeGroupRequest(title=title, description=description, overwrite=overwrite).to_dict()
        data['admin-pwd'] = self.pwd
        return self.send_request(f'groupmanagement/make/{identifier}', method='PUT', json=data)

    def delete_group(self, group: str) -> tuple[int, Any]:
        data = {'admin-pwd': self.pwd}
        return self.send_request(f'groupmanagement/delete/{group}', method='DELETE', json=data)

    def add_subgroup_to_group(self, group: str, subgroup: str) -> tuple[int, Any]:
        data = {'admin-pwd': self.pwd}
        return self.send_request(f'groupmanagement/addsubgroup/{group}/{subgroup}', method='PUT', json=data)

    def add_env_to_group(self, group: str, env: str) -> tuple[int, Any]:
        data = {'admin-pwd': self.pwd}
        return self.send_request(f'groupmanagement/addenv/{group}/{env}', method='PUT', json=data)

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

    def get_agent_results(self, env: Optional[str] = None):
        if env is not None:
            code, content = self.send_request(f'results/{env}', method='GET')
        else:
            code, content = self.send_request('results', method='GET')
        assert code == 200
        return content

    def remove_nonrecent_runs(self):
        code, content = self.send_request('removenonrecentruns', method='GET', json={'admin-pwd': self.pwd})
        assert code == 200
        return content

    def upload_plugin(self, package: Path | str):
        package = Path(package)
        assert package.is_dir()

        package = Path(package)

        data = io.BytesIO()
        with ZipFile(data, 'w') as zf:
            for file_path in package.rglob("*"):
                rel_path = file_path.relative_to(package.parent)
                if '__pycache__' in str(rel_path) or '.mypy_cache' in str(rel_path):
                    continue
                logger.debug(f'Including {rel_path}')
                zf.write(file_path, arcname=rel_path)

        encoded_pwd = (
            base64.
            encodebytes(self.pwd.encode())
            .decode()
            .replace('\n', '')  # no linebreaks in header
        )
        return self.send_request('/uploadplugin', method='PUT', data=data.getvalue(),
                                 headers={'Authorization': f'Basic {encoded_pwd}'})
