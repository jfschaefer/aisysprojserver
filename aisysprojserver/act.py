import dataclasses
from typing import Any
import re

from dataclasses_json import dataclass_json, Undefined
from flask import Blueprint, g, request, jsonify
from sqlalchemy import select
from werkzeug.exceptions import BadRequest

from aisysprojserver import models
from aisysprojserver.active_env import ActiveEnvironment
from aisysprojserver.agent_account import AgentAccount
from aisysprojserver.agent_data import AgentData
from aisysprojserver.env_interface import GenericEnvironment, RunData, ActionHistoryEntry
from aisysprojserver.json_util import json_load, json_dump
from aisysprojserver.models import AgentDataModel, RunModel, KeyValAccess

bp = Blueprint('act', __name__)

_run_id_regex = re.compile('^(?P<runid>[0-9]+)#(?P<actionno>[0-9]+)$')


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclasses.dataclass(frozen=True)
class ActConfig:
    single_request: bool = False  # respond with at most 1 action request


class ActManager:
    def __init__(self, env_id: str, content):
        self.env_id = env_id
        self.content: str = content

        self.active_env: ActiveEnvironment = ActiveEnvironment(env_id)
        if not self.active_env.exists():
            raise BadRequest(f'No such environment {env_id}')

        self.account = AgentAccount.from_request(env_id)
        self.account.require_authenticated()
        self.account.require_active()

        # self.act_config: ActConfig = ActConfig.schema().load(content['config'] if 'config' in content else {})
        self.act_config: ActConfig = ActConfig.schema().load(content)

        self.env: GenericEnvironment = self.active_env.get_env_instance()

        self.errors: list[str] = []
        self.messages: list[str] = []

    def process_action(self, action_json: dict):
        # check that action_json is well-formed
        if not (isinstance(action_json, dict) and 'run' in action_json and 'action' in action_json):
            self.errors.append(f'Malformed content: {json_dump(action_json)}')
            return
        if (match := _run_id_regex.match(action_json['run'])) is None:
            print(action_json['run'])
            self.errors.append(f'Malformed run identifier')
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
                self.errors.append(f'Invalid run id {action_json["run"]}')
                return
            if run_model.agent != self.account.identifier:
                self.errors.append(f'Run id {run_id} does not reference one of your agent\'s runs')
                return

            history = json_load(run_model.history)
            if len(history) != action_no:
                self.errors.append(f'Wrong action number for {action_json["run"]} (the action might have been '
                                   f'intended for an earlier state)')
                return

            # STEP 2: PERFORM ACTION
            action_result = self.env.act(action_json['action'], RunData(
                action_history=[ActionHistoryEntry(action, extra) for action, extra in history],
                state=json_load(run_model.state),
                outcome=None,
                agent_name='/'.join(run_model.agent.split('/')[1:]),
                run_id=run_model.identifier,
            ))

            # STEP 3: PROCESS ACTION RESULT
            if action_result.new_state is None:  # error
                if action_result.message:
                    self.errors.append(action_result.message)
                else:
                    self.errors.append(
                        f'The environment failed to update the state for {action_json["run"]} - this is a server error')
                return

            if action_result.message:
                self.messages.append(f'{action_json["run"]}: {action_result.message}')

            run_model.state = json_dump(action_result.new_state)
            history.append([action_json['action'], action_result.action_extra_info])
            run_model.history = json_dump(history)

            if action_result.outcome is not None:
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

        return agent_data.total_runs % 7319 == 0  # Reasoning: We should do the cleanup too often because it can mess with debugging.

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

    def get_act_response(self):
        response = {'errors': self.errors, 'messages': self.messages}
        max_requests: int = self.env.settings.NUMBER_OF_ACTION_REQUESTS
        if self.act_config.single_request:
            max_requests = 1

        with models.Session() as session:
            def serialize_run(run: RunModel):
                run.outstanding_action = True
                session.add(run)
                history = json_load(run.history)
                rd = RunData([ActionHistoryEntry(a, e) for a, e in history], json_load(run.state), None,
                             run_id=run.identifier, agent_name='/'.join(run.agent.split('/')[1:]))
                ar = self.env.get_action_request(rd)
                return {'run': f'{run.identifier}#{len(history)}',
                        'percept': ar.content}

            query = select(RunModel).where(RunModel.finished == False, RunModel.agent == self.account.identifier)
            runs: list[RunModel] = list(session.scalars(query))
            runs.sort(key=lambda run: run.identifier)

            runs_with_outstanding_action = [run for run in runs if run.outstanding_action]
            if runs_with_outstanding_action:
                response['action-requests'] = [serialize_run(run) for run in
                                               runs_with_outstanding_action[:max_requests]]
                session.commit()
                return response

            while len(runs) < max_requests:
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

            runs = runs[:max_requests]
            response['action-requests'] = [serialize_run(run) for run in runs]
            session.commit()
            return response


@bp.route('/act/<env_id>', methods=['GET', 'PUT'])
def act(env_id: str):
    g.isJSON = True
    content = request.get_json()
    if not content:
        raise BadRequest('Expected JSON body')

    actor = ActManager(env_id, content)

    actions = content['actions'] if 'actions' in content else []
    for action in actions:
        actor.process_action(action)

    return jsonify(actor.get_act_response())
