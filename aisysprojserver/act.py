import dataclasses
import re
from enum import Enum
from typing import Any, Optional

from flask import g, request, jsonify
from pydantic import BaseModel, Field
from sqlalchemy import select
from werkzeug.exceptions import BadRequest

from aisysprojserver import models, telemetry
from aisysprojserver.active_env import ActiveEnvironment
from aisysprojserver.agent_account import AgentAccount
from aisysprojserver.agent_data import AgentData
from aisysprojserver.env_interface import GenericEnvironment, RunData, ActionHistoryEntry
from aisysprojserver.models import AgentDataModel, RunModel, KeyValAccess
from aisysprojserver.telemetry import MonitoredBlueprint
from aisysprojserver.util import json_load, json_dump, PYDANTIC_REQUEST_CONFIG, parse_request

bp = MonitoredBlueprint('act', __name__)

_run_id_regex = re.compile('^(?P<runid>[0-9]+)#(?P<actionno>[0-9]+)$')


@dataclasses.dataclass(frozen=True)
class ActConfig:
    parallel_runs: bool = True


class Action(BaseModel):
    model_config = PYDANTIC_REQUEST_CONFIG

    run: str
    action: Any


class ActionRequest(BaseModel):
    model_config = PYDANTIC_REQUEST_CONFIG

    run: str
    percept: Any


class RequestV0(BaseModel):
    model_config = PYDANTIC_REQUEST_CONFIG

    agent: str
    pwd: str
    actions: list[Action] = Field(default_factory=list)
    single_request: bool = Field(default=False, serialization_alias='single-request')

    def to_v1(self) -> 'RequestV1':
        return RequestV1(
            agent=self.agent,
            pwd=self.pwd,
            actions=self.actions,
            parallel_runs=not self.single_request,
            client=''
        )


class ResponseV0(BaseModel):
    model_config = PYDANTIC_REQUEST_CONFIG

    errors: list[str] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)
    action_requests: list[ActionRequest] = Field(default_factory=list, serialization_alias='action-requests')


class RequestV1(BaseModel):
    model_config = PYDANTIC_REQUEST_CONFIG

    agent: str
    pwd: str
    actions: list[Action] = Field(default_factory=list)
    parallel_runs: bool = Field(default=True, serialization_alias='parallel-runs')
    to_abandon: list[str] = Field(default_factory=list, serialization_alias='to-abandon')
    client: str = ''


class MessageType(str, Enum):
    error = 'error'
    warning = 'warning'
    info = 'info'


class Message(BaseModel):
    model_config = PYDANTIC_REQUEST_CONFIG

    run: Optional[str] = None
    content: Any
    type: MessageType


class ResponseV1(BaseModel):
    model_config = PYDANTIC_REQUEST_CONFIG

    action_requests: list[ActionRequest] = Field(default_factory=list, serialization_alias='action-requests')
    active_runs: list[str] = Field(default_factory=list, serialization_alias='active-runs')
    messages: list[Message] = Field(default_factory=list)
    finished_runs: dict[str, Any] = Field(default_factory=dict, serialization_alias='finished-runs')

    def to_v0(self) -> ResponseV0:
        def fmt_msg(m: Message) -> str:
            return f'{m.type}: Run {m.run}: {m.content}'
        return ResponseV0(
            errors=[fmt_msg(m) for m in self.messages if m.type == MessageType.error],
            messages=[fmt_msg(m) for m in self.messages if m.type != MessageType.error],
            action_requests=self.action_requests
        )


class ActManager:
    def __init__(self, env_id: str, request: RequestV1):
        self.env_id = env_id
        self.offer_parallel_runs = request.parallel_runs

        self.active_env: ActiveEnvironment = ActiveEnvironment(env_id)
        if not self.active_env.exists():
            raise BadRequest(f'No such environment {env_id}')

        self.account = AgentAccount.from_request(env_id)
        self.account.require_authenticated()
        self.account.require_active()

        self.env: GenericEnvironment = self.active_env.get_env_instance()

        self.messages: list[Message] = []
        self.finished_runs: dict[str, Any] = {}

    def process_action(self, action: Action):
        if (match := _run_id_regex.match(action.run)) is None:
            self.messages.append(Message(content=f'Malformed run identifier {match!r}', type=MessageType.error))
            return
        run_id = int(match.group('runid'))
        action_no = int(match.group('actionno'))

        do_cleanup: bool = False

        with models.Session() as session:
            # we do a separate transaction for each action - less efficient, but
            # more robust if we want to parallelize

            # STEP 1: LOAD MODELS
            # Note: we do not use the Run class as a wrapper because everything should happen in the same session
            # (which is not supported by the wrapper)
            run_model: RunModel = session.get(RunModel, run_id)
            if not run_model:
                self.messages.append(Message(run=action.run, content='Invalid run id', type=MessageType.error))
            if run_model.agent != self.account.identifier:
                self.messages.append(
                    Message(run=action.run, content='This run does not belong to your agent', type=MessageType.error))
                return

            history = json_load(run_model.history)
            if len(history) != action_no:
                self.messages.append(Message(
                    run=action.run,
                    content=f'Wrong action number {action_no} '
                            '(the action might have been for an earlier action request)',
                    type=MessageType.error
                ))
                return

            # STEP 2: PERFORM ACTION
            action_result = self.env.act(action.action, RunData(
                action_history=[ActionHistoryEntry(action, extra) for action, extra in history],
                state=json_load(run_model.state),
                outcome=None,
                agent_name='/'.join(run_model.agent.split('/')[1:]),
                run_id=run_model.identifier,
            ))

            # STEP 3: PROCESS ACTION RESULT
            if action_result.new_state is None:  # error
                if action_result.message:
                    self.messages.append(Message(run=action.run, content=action_result.message, type=MessageType.error))
                else:
                    self.messages.append(Message(
                        run=action.run,
                        content='Internal server error when trying to update the state',
                        type=MessageType.error
                    ))
                return

            if action_result.message:
                self.messages.append(Message(run=action.run, content=action_result.message, type=MessageType.info))

            run_model.state = json_dump(action_result.new_state)
            history.append([action.action, action_result.action_extra_info])
            run_model.history = json_dump(history)

            if action_result.outcome is not None:
                self.finished_runs[action.run] = action_result.outcome
                do_cleanup = self.process_outcome(action_result.outcome, run_model, session)

            run_model.outstanding_action = False
            session.add(run_model)
            session.commit()

        if do_cleanup:
            AgentData(self.account.identifier).delete_nonrecent_runs()

    def process_outcome(self, outcome: Any, run_model: RunModel, session) -> bool:
        """ returns True iff cleanup is recommended """
        agent_data = self.get_agent_data_model(session)
        run_model.outcome = json_dump(outcome)
        run_model.finished = True
        agent_data.total_runs += 1

        # UPDATE RATINGS
        if agent_data.total_runs >= self.env.settings.MIN_RUNS_FOR_FULLY_EVALUATED:
            agent_data.fully_evaluated = True

        results = json_load(agent_data.recent_results)
        results.append(outcome)

        match self.env.settings.RATING_STRATEGY:
            case 'average':
                results = results[-self.env.settings.MIN_RUNS_FOR_FULLY_EVALUATED:]
                agent_data.current_rating = sum(results) / len(results)
            case other:
                raise Exception(f'Unsupported RATING_STRATEGY {other}')

        if agent_data.fully_evaluated:
            if self.env.settings.RATING_OBJECTIVE == 'max':
                agent_data.best_rating = max(agent_data.best_rating, agent_data.current_rating)
            else:
                assert self.env.settings.RATING_OBJECTIVE == 'min'
                agent_data.best_rating = min(agent_data.best_rating, agent_data.current_rating)

        agent_data.recent_results = json_dump(results)

        # UPDATE HISTORY OF RECENT RUNS
        runs = json_load(agent_data.recently_finished_runs)
        runs.append(run_model.identifier)
        agent_data.recently_finished_runs = json_dump(runs[-20:])

        kva = KeyValAccess(session)
        key = self.active_env.recent_runs_key
        runs2 = json_load(kva[key] or '[]')
        runs2.append(run_model.identifier)
        kva[key] = json_dump(runs2[-20:])

        session.add(agent_data)

        # Reasoning: We should do the cleanup too often because it can mess with debugging.
        return agent_data.total_runs % 2351 == 0

    def get_agent_data_model(self, session) -> AgentDataModel:
        agent_data_model = session.get(AgentDataModel, self.account.identifier)
        if not agent_data_model:
            agent_data_model = AgentDataModel(
                identifier=self.account.identifier,
                environment=self.env_id,
                total_runs=0,
                fully_evaluated=False,
                recently_finished_runs='[]',
                recent_results='[]',
                best_rating=self.env.settings.INITIAL_RATING,
                current_rating=self.env.settings.INITIAL_RATING,
            )
        return agent_data_model

    def get_act_response(self) -> ResponseV1:
        response = ResponseV1(messages=self.messages, finished_runs=self.finished_runs)
        max_requests: int = self.env.settings.NUMBER_OF_ACTION_REQUESTS
        if not self.offer_parallel_runs:
            max_requests = 1

        with models.Session() as session:
            def serialize_run(run: RunModel) -> ActionRequest:
                run.outstanding_action = True
                session.add(run)
                history = json_load(run.history)
                rd = RunData([ActionHistoryEntry(a, e) for a, e in history], json_load(run.state), None,
                             run_id=run.identifier, agent_name='/'.join(run.agent.split('/')[1:]))
                ar = self.env.get_action_request(rd)
                return ActionRequest(run=f'{run.identifier}#{len(history)}', percept=ar.content)

            query = select(RunModel).where(
                RunModel.finished == False,  # noqa: E712
                RunModel.agent == self.account.identifier
            )
            runs: list[RunModel] = list(session.scalars(query))
            runs.sort(key=lambda run: run.identifier)

            runs_with_outstanding_action = [run for run in runs if run.outstanding_action]
            if runs_with_outstanding_action:
                for run in runs_with_outstanding_action[:max_requests]:
                    response.action_requests.append(serialize_run(run))
                for run in runs:
                    response.active_runs.append(str(run.identifier))
                session.commit()
                return response

            while len(runs) < max_requests:
                with telemetry.measure_run_creation_duration(self.active_env.env_class_refstr):
                    state = self.env.new_run()
                new_run = RunModel(
                    environment=self.env_id,
                    agent=self.account.identifier,
                    finished=False,
                    outstanding_action=False,
                    state=json_dump(state),
                    history='[]',
                    outcome=json_dump(None)
                )
                session.add(new_run)
                session.commit()
                runs.append(new_run)

            for run in runs:
                response.active_runs.append(str(run.identifier))
            runs = runs[:max_requests]
            for run in runs:
                response.action_requests.append(serialize_run(run))
            session.commit()
            return response


@bp.route('/act/<env_id>', methods=['GET', 'PUT'])
def act(env_id: str):
    g.isJSON = True
    content = request.get_json()
    if not content:
        raise BadRequest('Expected JSON body')

    protocol_version = 0
    if 'protocol-version' in content:
        protocol_version = content['protocol-version']

    request_data: RequestV1

    if protocol_version == 0:
        request_data = parse_request(RequestV0, content).to_v1()
    elif protocol_version == 1:
        request_data = parse_request(RequestV1, content)
    else:
        raise BadRequest(f'Unsupported protocol version {protocol_version!r}')

    actor = ActManager(env_id, request_data)

    telemetry.report_action(env_id, len(request_data.actions))

    for action in request_data.actions:
        with telemetry.measure_action_processing(actor.active_env.env_class_refstr):
            actor.process_action(action)

    response = actor.get_act_response()
    if protocol_version == 0:
        return jsonify(response.to_v0().model_dump(by_alias=True))

    return jsonify(response.model_dump(by_alias=True))
