from aisysprojserver.plugins import PluginManager
from aisysprojserver_test.servertestcase import ServerTestCase


class PluginTest(ServerTestCase):
    def test_import_simple_nim(self):
        self.require_standard_setup()
        self.assertEqual(PluginManager.plugins['simple_nim'].version, '0.0.1')
