import subprocess

from flask import Blueprint, g, jsonify

from aisysprojserver import config
from aisysprojserver.authentication import require_admin_auth


ERROR_BUFFER: list[str] = []


bp = Blueprint('admin', __name__)


@bp.route('/diskusage')
def diskusage():
    g.isJSON = True
    require_admin_auth()
    return jsonify(subprocess.check_output(['du', '-h', '--max-depth=1'], cwd=config.get().PERSISTENT).decode() +\
                   subprocess.check_output(['ls', '-lh'], cwd=config.get().PERSISTENT).decode())


@bp.route('/errors')
def errors():
    g.isJSON = True
    require_admin_auth()
    return jsonify(ERROR_BUFFER)
