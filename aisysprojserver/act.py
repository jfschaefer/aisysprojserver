import dataclasses
import json
import re

from dataclasses_json import dataclass_json, Undefined
from flask import Blueprint, g, request
from werkzeug.exceptions import BadRequest

from aisysprojserver.active_env import ActiveEnvironment
from aisysprojserver.agent_account import AgentAccount
from aisysprojserver.agent_data import AgentDataWrapper
from aisysprojserver.env_interface import GenericEnvironment, RunData, ActionHistoryEntry
from aisysprojserver.models import Session, AgentDataModel, RunModel
from aisysprojserver.runwrapper import RunWrapper

bp = Blueprint('active_env_management', __name__)

_run_id_regex = re.compile('^(?P<runid>[0-9]+)#(?P<actionno>[0-9]+)$')


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclasses.dataclass(frozen=True)
class ActConfig:
    single_request: bool = False  # respond with at most 1 action request


@bp.route('/act/<env>', methods=['GET', 'PUT'])
def act(env: str):
    g.isJSON = True
    content = request.get_json()
    if not content:
        raise BadRequest('Expected JSON body')

    # GET GENERIC DATA
    active_env = ActiveEnvironment(env)
    if not active_env.exists():
        raise BadRequest(f'No such environment {env}')

    account = AgentAccount.from_request(env)
    account.require_authenticated()
    account.require_active()

    act_config = ActConfig.schema().load(content['config'] if 'config' in content else {})

    actual_env: GenericEnvironment = active_env.get_env_instance()

    errors: list[str] = []
    messages: list[str] = []

    # EXECUTE ACTIONS

    actions = content['actions'] if 'actions' in content else []
    for action in actions:
        if not (isinstance(action, dict) and 'run' in action and 'action' in action):
            errors.append(f'Malformed content: {json.dumps(action)}')
            continue
        if (match := _run_id_regex.match(action['run'])) is None:
            errors.append(f'Malformed run identifier')
            continue
        run_id = int(match.group('runid'))
        action_no = int(match.group('actionno'))

        with Session() as session:
            # we do a separate transaction for each action - less efficient, but
            # more robust if we want to parallelize
            agent_data_model = session.get(AgentDataModel, account.identifier)
            if agent_data_model:
                agent_data = AgentDataWrapper(actual_env, agent_data_model)
            else:
                agent_data = AgentDataWrapper.new(account.identifier, env, actual_env)

            run_model = session.get(RunModel, run_id)
            if not run_model:
                errors.append(f'Invalid run id {action["run"]}')
                continue
            run = RunWrapper(actual_env, run_model)
            if len(run.history) != action_no:
                errors.append(f'Wrong action number for {action["run"]} (the action might have been intended for an '
                              f'earlier state)')
                continue

            action_result = actual_env.act(action['action'], RunData(
                action_history=[ActionHistoryEntry(action, extra) for action, extra in run.history],
                state=run.model.state,
                outcome=None
            ))

            if action_result.new_state is None:   # error
                if action_result.message:
                    errors.append(action_result.message)
                else:
                    errors.append(f'The environment failed to update the state for {action["run"]} - this is a server error')
                continue

            if action_result.message:
                messages.append(f'{action["run"]}: {action_result.message}')

            run.model.state = action_result.new_state
            run.history.append([action['action'], action_result.action_extra_info])
            if action_result.outcome is not None:
                ... # TODO: continue
