"""A more sophisticated AISysProj server client implementation than in ``client_simple_v1.py``."""

import abc
import dataclasses
import json
import logging
import multiprocessing
import time
from pathlib import Path
from typing import TypedDict, Optional, Callable, Any, Literal

import requests as requests_lib

logger = logging.getLogger(__name__)

# type info (not using e.g. pydantic to keep dependencies minimal)
AgentConfig = TypedDict('AgentConfig', {'agent': str, 'env': str, 'url': str, 'pwd': str})
Action = TypedDict('Action', {'run': str, 'act_no': int, 'action': Any})
ActionRequest = TypedDict('ActionRequest', {'run': str, 'act_no': int, 'percept': Any})
Message = TypedDict('Message', {'type': Literal['info', 'warning', 'error'], 'content': str, 'run': Optional[str]})
ServerResponse = TypedDict(
    'ServerResponse',
    {
        'action_requests': list[ActionRequest],
        'active_runs': list[str],
        'messages': list[Message],
        'finished_runs': dict[str, Any],
    }
)


def _handle_response(response) -> Optional[ServerResponse]:
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 503:
        logger.warning('Server is busy - retrying in 3 seconds')
        time.sleep(3)
        return None
    else:  # in other cases, retrying does not help (authentication problems, etc.)
        logger.error(f'Status code {response.status_code}.')
        j = response.json()
        logger.error(f'{j["errorname"]}: {j["description"]}')
        logger.error('Stopping.')
        response.raise_for_status()
        return None     # unreachable, but mypy doesn't know that


def send_request(
        config: AgentConfig,
        actions: list[Action],
        *,
        to_abandon: Optional[list[str]] = None,
        parallel_runs: bool = True
) -> ServerResponse:
    while True:  # retry until success
        logger.debug(f'Sending request with {len(actions) or "no"} actions: {actions}')
        base_url = config['url']
        if not base_url.endswith('/'):
            base_url += '/'
        response = requests_lib.put(f'{base_url}act/{config["env"]}', json={
            'protocol_version': 1,
            'agent': config['agent'],
            'pwd': config['pwd'],
            'actions': actions,
            'to_abandon': to_abandon or [],
            'parallel_runs': parallel_runs,
            'client': 'py-client-v1',
        })
        result = _handle_response(response)
        if result is not None:
            return result


@dataclasses.dataclass(frozen=True)
class RequestInfo:
    run_url: str
    action_number: int
    run_id: str


class _RunTracker:
    def __init__(self):
        self.number_of_new_runs_finished: int = 0
        self.old_runs: Optional[set[str]] = None
        self.ongoing_runs: set[str] = set()

    def update(self, response: ServerResponse):
        if self.old_runs is None:
            self.old_runs = set(response['active_runs'])
            for rq in response['action_requests']:
                if rq['act_no'] == 0:  # not actually old
                    self.old_runs.remove(rq['run'])

        ongoing_runs = set(response['active_runs'])
        self.number_of_new_runs_finished += len(self.ongoing_runs - ongoing_runs)
        self.ongoing_runs = ongoing_runs


class RequestProcessor(abc.ABC):
    @abc.abstractmethod
    def process_requests(self, requests: list[tuple[Any, RequestInfo]], counter: _RunTracker) -> list[Action]:
        pass

    def close(self):
        pass

    def on_new_run(self, run_id: str):
        logger.info(f'Starting new run ({run_id})')

    def on_finished_run(self, run_id: str, url: str, outcome: Any):
        logger.info(f'Finished run {run_id} with outcome {json.dumps(outcome)}')
        logger.info(f'You can view the run at {url}')


class SimpleRequestProcessor(RequestProcessor):
    def __init__(self, action_function: Callable[[Any, RequestInfo], Any], processes: int = 1):
        self.action_function = action_function
        self.pool = None
        if processes > 1:
            self.pool = multiprocessing.Pool(processes=processes)

    def process_requests(self, requests: list[tuple[Any, RequestInfo]], counter: _RunTracker) -> list[Action]:
        if self.pool is None:
            return [
                {
                    'run': request_info.run_id,
                    'act_no': request_info.action_number,
                    'action': self.action_function(percept, request_info)
                } for percept, request_info in requests
            ]
        else:
            return [
                {
                    'run': request_info.run_id,
                    'act_no': request_info.action_number,
                    'action': action
                } for action, (_percept, request_info) in zip(
                    self.pool.starmap(self.action_function, requests),
                    requests
                )
            ]

    def close(self):
        if self.pool is not None:
            self.pool.terminate()


def run(
        agent_config_file: str | Path,
        agent_function: Callable[[Any, RequestInfo], Any],
        *,
        parallel_runs: bool = True,
        processes: int = 1,
        run_limit: Optional[int] = None,
):
    agent_config = json.loads(Path(agent_config_file).read_text())

    def get_run_url(run_id: str) -> str:
        url = agent_config['url']
        if not url.endswith('/'):
            url += '/'
        return url + f'run/{agent_config["env"]}/{run_id}'

    request_processor = SimpleRequestProcessor(agent_function, processes=processes)
    counter = _RunTracker()

    actions_to_send: list[Action] = []

    try:
        while True:
            response = send_request(agent_config, actions_to_send, parallel_runs=parallel_runs)

            counter.update(response)

            if run_limit is not None and counter.number_of_new_runs_finished >= run_limit:
                logger.info(f'Stopping after {run_limit} runs.')
                break

            requests = [
                (ar['percept'], RequestInfo(get_run_url(ar['run']), ar['act_no'], ar['run']))
                for ar in response['action_requests']
            ]

            for r in requests:
                if r[1].action_number == 0:
                    request_processor.on_new_run(r[1].run_id)

            for run_id, outcome in response['finished_runs'].items():
                request_processor.on_finished_run(run_id, get_run_url(run_id), outcome)

            actions_to_send = request_processor.process_requests(requests, counter)

    finally:
        request_processor.close()
        logger.info('Finished.')
