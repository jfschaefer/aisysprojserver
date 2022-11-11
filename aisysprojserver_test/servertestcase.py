import json
import unittest
from pathlib import Path
from typing import Any, Optional

from flask import Flask, url_for
from flask.testing import FlaskClient

from aisysprojserver import config, models
from aisysprojserver.app import create_app
from aisysprojserver_clienttools.admin import AdminClient
from aisysprojserver_clienttools.upload_plugin import upload_plugin


class TestAdmin(AdminClient):
    def __init__(self, baseurl: str, authentication: str, client: FlaskClient):
        AdminClient.__init__(self, baseurl, authentication)
        self.client = client

    def send_request(self, path: str, **kwargs) -> tuple[int, Any]:
        response = self.client.open(path, **kwargs)
        return response.status_code, response.get_json()


class TestHelper(object):
    def __init__(self):
        self.configuration = config.TestConfig()
        self.app = create_app(self.configuration)
        self.flask_client = self.app.test_client()
        self.admin = TestAdmin(baseurl='http://localhost:5001',
                               authentication='test-admin-password',
                               client=self.flask_client)


class ServerTestCase(unittest.TestCase):
    helper: TestHelper = TestHelper()
    admin: TestAdmin = helper.admin
    app: Flask = helper.app
    client: FlaskClient = helper.flask_client
    _standard_setup_loaded: bool = False
    _testuser_content: dict[str, str]

    _username_counter: int = 0

    @classmethod
    def get_username(cls) -> str:
        """ Returns a unique username """
        username = f'user{cls._username_counter}'
        cls._username_counter += 1
        return username

    @classmethod
    def _load_standard_setup(cls):
        """ Load a basic setup (environment and agents) to support testing """
        models.Base.metadata.drop_all(bind=models.engine)
        models.Base.metadata.create_all(bind=models.engine)

        package = Path(__file__).parent.parent/'example_envs'/'simple_nim'
        assert package.is_dir(), f'{package} does not exist'
        code, content = upload_plugin(cls.admin, package)
        assert code == 200, 'Failed to upload plugin. Content: ' + str(content)

        cls.admin.make_env('simple_nim.environment:Environment', 'test-nim',
                           'Test Environment (Nim)', config='{}', overwrite=False)
        code, cls._testuser_content = cls.admin.new_user('test-nim', 'testuser')
        assert code == 200, 'Failed to create testuser'

        cls._standard_setup_loaded = True

#     def act_nim(self, username: Optional[str] = None, password: Optional[str] = None, try_win: bool = True,
#                 move: Optional[int] = None):
#         username = username or 'testuser'
#         password = password or self._testuser_pwd




    @classmethod
    def require_standard_setup(cls):
        if not cls._standard_setup_loaded:
            cls._load_standard_setup()
