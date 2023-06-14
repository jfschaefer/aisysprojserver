import subprocess

from flask import Blueprint, g, jsonify
from werkzeug.exceptions import NotFound

from aisysprojserver import config
from aisysprojserver.active_env import ActiveEnvironment
from aisysprojserver.authentication import require_admin_auth

ERROR_BUFFER: list[str] = []

bp = Blueprint('admin', __name__)


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


@bp.route('/results/<env_id>')
def results(env_id: str):
    g.isJSON = True
    active_env = ActiveEnvironment(env_id)
    if not active_env.exists():
        raise NotFound()

    result: list[dict] = []
    for agent in active_env.get_env_data().agents:
        result.append({
            'name': agent.agent_name,
            'rating': agent.agent_rating,
            'fully-evaluated': agent.fully_evaluated,
        })

    return jsonify(result)
