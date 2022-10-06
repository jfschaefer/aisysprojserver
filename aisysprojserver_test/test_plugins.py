from pathlib import Path

from aisysprojserver_test.servertestcase import ServerTestCase
from aisysprojserver_clienttools.upload_plugin import upload_plugin


class PluginTest(ServerTestCase):
    def test_import_simple_nim(self):
        self.load_standard_env()