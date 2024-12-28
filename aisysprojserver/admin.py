import subprocess

from flask import g, jsonify, request
from sqlalchemy import text
from werkzeug.exceptions import NotFound

from aisysprojserver import config, models
from aisysprojserver.active_env import ActiveEnvironment, get_all_active_envs
from aisysprojserver.agent_account import get_all_agentaccounts_for_env
from aisysprojserver.agent_data import get_all_agentdata, AgentData
from aisysprojserver.authentication import require_admin_auth
from aisysprojserver.group import get_all_groups
from aisysprojserver.telemetry import MonitoredBlueprint
from aisysprojserver.website import cache

ERROR_BUFFER: list[str] = []

bp = MonitoredBlueprint('admin', __name__)


@bp.route('/diskusage')
def diskusage():
    g.isJSON = True
    require_admin_auth()
    return jsonify(subprocess.check_output(['du', '-h', '--max-depth=1'], cwd=config.get().PERSISTENT).decode() +
                   subprocess.check_output(['ls', '-lh'], cwd=config.get().PERSISTENT).decode())


@bp.route('/errors')
def errors():
    g.isJSON = True
    require_admin_auth()
    return jsonify(ERROR_BUFFER)


def get_env_results(active_env: ActiveEnvironment):
    if not active_env.exists():
        raise NotFound()

    result: dict[str, dict] = {}
    for agent in active_env.get_env_data().agents:
        result[agent.agent_name] = {
            'rating': agent.agent_rating,
            'fully-evaluated': agent.fully_evaluated,
            'total-runs': agent.total_number_of_runs,
        }
    return result


@bp.route('/results/<env_id>')
@cache.cached(timeout=10)
def results_env(env_id: str):
    g.isJSON = True
    return jsonify(get_env_results(ActiveEnvironment(env_id)))


@bp.route('/results')
@cache.cached(timeout=10)
def results():
    g.isJSON = True
    envs_list: list[ActiveEnvironment] = get_all_active_envs()
    return jsonify({ae.identifier: get_env_results(ae) for ae in envs_list})


@bp.route('/removenonrecentruns')
def removenonrecentruns():
    g.isJSON = True
    require_admin_auth()
    content = request.get_json()
    if not (content and content['just-vacuum']):
        for agent_data in get_all_agentdata():
            agent_data.delete_nonrecent_runs()
    with models.Session() as session:
        session.execute(text('VACUUM'))
    return jsonify({'result': 'done'})


@bp.route('/getenvs')
@cache.cached(timeout=10)
def getenvs():
    g.isJSON = True
    require_admin_auth()
    result: dict[str, list[str]] = {}
    for ae in get_all_active_envs():
        result[ae.identifier] = []
    for group in get_all_groups():
        for env in group.get_envs():
            result[env.identifier].append(group.display_name)
    return jsonify(result)


@bp.route('/deleteunusedagents/<env_id>')
def deleteunusedagents(env_id: str):
    g.isJSON = True
    require_admin_auth()
    accounts = get_all_agentaccounts_for_env(env_id)
    for account in accounts:
        agent_data = AgentData(account.identifier)
        if not agent_data.exists():
            account.delete()
            continue
        if agent_data.to_agent_data_summary().total_number_of_runs == 0:
            account.delete()
            agent_data.delete()

    return jsonify({'result': 'done'})
