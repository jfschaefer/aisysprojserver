import json
import tempfile
from itertools import product
from pathlib import Path
from typing import Callable

from aisysprojserver_test.servertestcase import get_strong_nim_move, ServerTestCase


class SuccessException(Exception):
    pass


class ActTest(ServerTestCase):

    def simple_client_test(self, version: str, parallel_runs: bool, agent_config: Path):
        run: Callable   # type: ignore
        if version == 'simple_v0':
            from aisysprojserver_clienttools.client_simple_v0 import run
        elif version == 'simple_v1':
            from aisysprojserver_clienttools.client_simple_v1 import run
        elif version == 'client':
            from aisysprojserver_clienttools.client import run
        else:
            raise ValueError(f'Invalid version: {version}')

        counter = 0

        def _my_action_function(percept):
            nonlocal counter
            counter += 1
            if counter > 10:
                raise SuccessException()
            return get_strong_nim_move(percept)

        my_action_function: Callable   # type: ignore
        if version == 'client':
            my_action_function = lambda percept, _: _my_action_function(percept)
        else:
            my_action_function = _my_action_function

        import requests
        original_put = requests.put

        def myput(*args, **kwargs):
            # This is a hack to redirect requests to the flask test client
            arg_list = list(args)
            if arg_list[0].startswith(self.admin.base_url):
                arg_list[0] = arg_list[0][len(self.admin.base_url):]
            result = self.admin.send_request_raw(*arg_list, **kwargs)

            # the following hack makes it so that request.json is a function that returns the json, not the json itself
            # as the client expects from requests
            actual_json = result.json
            result.get_json = lambda: lambda: actual_json
            return result
        try:
            requests.put = myput
            self.assertRaises(
                SuccessException, run, agent_config, my_action_function, parallel_runs=parallel_runs
            )
        finally:
            requests.put = original_put

    def test_clients(self):
        self.require_standard_setup()
        # requires python 3.12
        # with tempfile.NamedTemporaryFile(delete_on_close=False) as fp:
        #     json.dump(self._testuser_content, fp)
        #     fp.close()

        with tempfile.TemporaryDirectory() as tmpdir:
            agent_config = Path(tmpdir) / 'agent_config.json'
            with agent_config.open('w') as fp:
                json.dump(self._testuser_content, fp)

            # test simple clients
            for version, parallel_runs in product(['simple_v0', 'simple_v1', 'client'], [True, False]):
                with self.subTest(version=version):
                    self.simple_client_test(version, parallel_runs, agent_config)
