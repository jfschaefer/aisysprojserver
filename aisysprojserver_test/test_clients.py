import itertools
import json
import tempfile
from contextlib import contextmanager
from itertools import product
from pathlib import Path
from typing import Callable, Any

from aisysprojserver_clienttools.client import AgentConfig, RequestInfo
from aisysprojserver_test.servertestcase import get_strong_nim_move, ServerTestCase


class SuccessException(Exception):
    pass


class ActTest(ServerTestCase):
    @contextmanager
    def _put_overwritten(self):
        # This is a hack to temporarily redirect requests to the flask test client
        import requests
        original_put = requests.put

        def myput(*args, **kwargs):
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
            yield
        finally:
            requests.put = original_put

    def simple_client_test(self, version: str, parallel_runs: bool, agent_config: Path | AgentConfig, **kwargs):
        run: Callable   # type: ignore
        if version == 'simple_v0':
            from aisysprojserver_clienttools.client_simple_v0 import run
        elif version == 'simple_v1':
            from aisysprojserver_clienttools.client_simple_v1 import run
        elif version == 'client':
            from aisysprojserver_clienttools.client import run
        else:
            raise ValueError(f'Invalid version: {version}')

        if version != 'client':
            assert isinstance(agent_config, Path)

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

        with self._put_overwritten():
            self.assertRaises(
                SuccessException,
                run, agent_config, my_action_function, parallel_runs=parallel_runs, **kwargs
            )

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
                with self.subTest(version=version, parallel_runs=parallel_runs):
                    self.simple_client_test(version, parallel_runs, agent_config)

    def test_advanced_client(self):
        self.require_standard_setup()
        from aisysprojserver_clienttools.client import Agent

        class MyAgent(Agent):
            def get_action(self, percept: Any, request_info: RequestInfo) -> Any:
                return get_strong_nim_move(percept)

        for abandon_old_runs, multiprocessing in itertools.product([True, False], [True, False]):
            with self.subTest(abandon_old_runs=abandon_old_runs, multiprocessing=multiprocessing):
                with self._put_overwritten():
                    MyAgent.run(self._testuser_content, parallel_runs=True, abandon_old_runs=abandon_old_runs,
                                multiprocessing=multiprocessing, run_limit=10)
