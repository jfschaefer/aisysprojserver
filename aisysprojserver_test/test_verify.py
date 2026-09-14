import json

from aisysprojserver_test.servertestcase import ServerTestCase


class TestVerify(ServerTestCase):
    def test_basic_verify(self):
        self.require_standard_setup()
        code, content = self.admin.setup_verify(
            'nim-verify',
            verifier='simple_nim.verifier:VERIFIER'
        )
        self.assertEqual(200, code)
        code, content = self.admin.send_request(
            '/verify/nim-verify',
            method='GET',
            data=json.dumps([5, 2, 0]).encode(),
        )
        self.assertEqual(200, code)
        self.assertEqual({'result': 'invalid start'}, content)
