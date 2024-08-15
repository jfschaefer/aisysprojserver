"""A more sophisticated AISysProj server client implementation than in ``client_simple.py``."""

import abc
import dataclasses
import json
import logging
import multiprocessing
import time
from pathlib import Path
from typing import TypedDict, TypeAlias, Optional, Callable

import requests as requests_lib

logger = logging.getLogger(__name__)

Json: TypeAlias = dict[str, 'Json'] | list['Json'] | str | int | float | bool | None


class AgentConfig(TypedDict):
    agent: str
    env: str
    url: str
    pwd: str


def _handle_response(response) -> Optional[dict[str, Json]]:
    if response.status_code == 200:
        return _handle_success_response(response)
    elif response.status_code == 503:
        logger.warning('Server is busy - retrying in 3 seconds')
        time.sleep(3)
        return None
    else:  # in other cases, retrying does not help (authentication problems, etc.)
        logger.error(f'Status code {response.status_code}. Stopping.')
        response.raise_for_status()


def _handle_success_response(response) -> Optional[dict[str, Json]]:
    response_json = response.json()
    for error in response_json['errors']:
        logger.error(f'Error message from server: {error}')
    for message in response_json['messages']:
        logger.info(f'Message from server: {message}')

    action_requests = response_json['action-requests']
    if action_requests:
        return {
            action_request['run']: action_request['percept']
            for action_request in action_requests
        }
    else:
        logger.info('The server has no new action requests - waiting for 1 second.')
        time.sleep(1)  # wait a moment to avoid overloading the server and then try again
        return None


def send_request(config: AgentConfig, actions: dict[str, Json], single_request: bool = False) -> dict[str, Json]:
    while True:  # retry until success
        logger.info(f'Sending request with {len(actions) or "no"} actions: {actions}')
        base_url = config['url']
        if not base_url.endswith('/'):
            base_url += '/'
        response = requests_lib.put(f'{base_url}act/{config["env"]}', json={
            'agent': config['agent'],
            'pwd': config['pwd'],
            'actions': [
                {
                    'run': run_id,
                    'action': action,
                } for run_id, action in actions.items()
            ],
            'single_request': single_request,
        })
        result = _handle_response(response)
        if result is not None:
            return result


@dataclasses.dataclass(frozen=True)
class RequestInfo:
    run_url: str
    action_number: int
    run_number: int
    identifier: str

    @classmethod
    def create(cls, identifier: str, agent_config: AgentConfig) -> 'RequestInfo':
        run_number, action_number = identifier.split('#')
        url = agent_config['url']
        if not url.endswith('/'):
            url += '/'
        url += f'run/{agent_config["env"]}/{run_number}'
        return cls(
            run_url=url,
            action_number=int(action_number),
            run_number=int(run_number),
            identifier=identifier,
        )


class _RunTracker:
    def __init__(self):
        self.old_runs: set[int] = set()
        self.old_runs_finalized: bool = False
        self.ongoing_runs: dict[int, int] = {}
        self.number_finished_runs_nonold: int = 0

    def update(self, ris: list[RequestInfo]):
        # step 1: check if there are repeated requests
        # idea: if the agent send an invalid action, the server will send the same request again,
        # but it will not send requests for other on-going runs (to avoid cheating by delaying the finish of a run)

        is_repeat = False
        for ri in ris:
            if ri.run_number in self.ongoing_runs and self.ongoing_runs[ri.run_number] == ri.action_number:
                is_repeat = True
                break

        # step 2: update ongoing/old runs
        for ri in ris:
            if ri.run_number in self.ongoing_runs:
                self.ongoing_runs[ri.run_number] = ri.action_number
            elif ri.action_number == 0:
                self.ongoing_runs[ri.run_number] = 0
            else:  # it must be an old run
                if self.old_runs_finalized:
                    logger.warning('Unexpectedly got an old run request. This may happen '
                                   'when switching from parallel to single requests.')
                    self.number_finished_runs_nonold = 0
                    self.old_runs.add(ri.run_number)
                else:
                    self.old_runs.add(ri.run_number)
                    self.ongoing_runs[ri.run_number] = ri.action_number

        # step 3: check if old runs are finalized
        if not is_repeat and self.ongoing_runs:
            self.old_runs_finalized = True  # by now we should have received requests for all old runs

        # step 4: remove and count finished runs
        if not is_repeat:
            active = set(ri.run_number for ri in ris)
            for run_number in list(self.ongoing_runs):
                if run_number not in active:
                    del self.ongoing_runs[run_number]
                    if run_number not in self.old_runs:
                        self.number_finished_runs_nonold += 1


class RequestProcessor(abc.ABC):
    @abc.abstractmethod
    def process_requests(self, requests: list[tuple[Json, RequestInfo]], counter: _RunTracker) -> dict[str, Json]:
        pass

    def close(self):
        pass


class SimpleRequestProcessor(RequestProcessor):
    def __init__(self, action_function: Callable[[Json, RequestInfo], Json], processes: int = 1):
        self.action_function = action_function
        self.pool = None
        if processes > 1:
            self.pool = multiprocessing.Pool(processes=processes)

    def process_requests(self, requests: list[tuple[Json, RequestInfo]], counter: _RunTracker) -> dict[str, Json]:
        if self.pool is None:
            return {
                request_info.identifier: self.action_function(percept, request_info)
                for percept, request_info in requests
            }
        else:
            return {
                request[1].identifier: action
                for action, request in zip(
                    self.pool.starmap(self.action_function, requests),
                    requests
                )
            }

    def close(self):
        if self.pool is not None:
            self.pool.terminate()


def run(
        agent_function: Callable[[Json, RequestInfo], Json],
        agent_config_file: str | Path,
        *,
        parallel_runs: bool = True,
        processes: int = 1,
        run_limit: Optional[int] = None,
):
    agent_config = json.loads(Path(agent_config_file).read_text())

    request_processor = SimpleRequestProcessor(agent_function, processes=processes)
    counter = _RunTracker()

    actions_to_send: dict[str, Json] = {}

    try:
        while True:
            new_requests_raw = send_request(agent_config, actions_to_send, single_request=not parallel_runs)
            requests = [
                (percept, RequestInfo.create(identifier, agent_config))
                for identifier, percept in new_requests_raw.items()
            ]
            counter.update([ri for _, ri in requests])

            if run_limit is not None and counter.number_finished_runs_nonold >= run_limit:
                logger.info(f'Stopping after {run_limit} runs.')
                break

            for r in requests:
                if r[1].action_number == 0:
                    logger.info(f'Starting new run: {r[1].run_url}')

            actions_to_send = request_processor.process_requests(requests, counter)

    finally:
        request_processor.close()
        logger.info('Finished.')
