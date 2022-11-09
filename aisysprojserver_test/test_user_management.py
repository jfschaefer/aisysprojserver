from aisysprojserver_test.servertestcase import ServerTestCase


class TestUserManagement(ServerTestCase):
    def test_overwrite(self):
        self.require_standard_setup()
        username = self.get_username()
        self.assertEqual(self.admin.new_user('test-nim', username, overwrite=False)[0], 200)
        self.assertEqual(self.admin.new_user('test-nim', username, overwrite=False)[0], 400)
