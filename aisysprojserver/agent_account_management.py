import re

from flask import Blueprint, request, jsonify, g
from werkzeug.exceptions import BadRequest

from aisysprojserver.active_env import ActiveEnvironment
from aisysprojserver.agent_account import AgentAccount
from aisysprojserver.authentication import require_admin_auth

bp = Blueprint('agent_account_management', __name__)


@bp.route('/makeagent/<env>/<agent>', methods=['POST'])
def makeagent(env: str, agent: str):
    g.isJSON = True
    content = request.get_json()
    if not content:
        raise BadRequest('Expected JSON body')
    require_admin_auth()

    active_env = ActiveEnvironment(env)
    if not active_env.exists():
        raise BadRequest(f'No such environment {env}')

    if not re.match(r'[a-zA-Z0-9 \[\]_()-]+', agent):
        return BadRequest(f'Illegal agent name "{agent}"')
    agent_account = AgentAccount(env, agent)
    password = agent_account.signup(overwrite='overwrite' in content and content['overwrite'])

    return jsonify({
        'agent': agent,
        'pwd': password,
        'env': env,
    })


@bp.route('/blockagent/<env>/<agent>', methods=['PUT'])
def blockagent(env: str, agent: str):
    g.isJSON = True
    account = AgentAccount.from_request(env, agent)
    if not account.is_authenticated():
        require_admin_auth()
    account.block()


@bp.route('/unblockagent/<env>/<agent>', methods=['PUT'])
def unblockagent(env: str, agent: str):
    g.isJSON = True
    account = AgentAccount.from_request(env, agent)
    require_admin_auth()
    account.unblock()
