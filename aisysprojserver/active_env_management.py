import re
from typing import Any

from flask import request, g, jsonify
from pydantic import BaseModel
from werkzeug.exceptions import BadRequest

from aisysprojserver.active_env import ActiveEnvironment
from aisysprojserver.authentication import require_admin_auth
from aisysprojserver.plugins import PluginManager
from aisysprojserver.telemetry import MonitoredBlueprint
from aisysprojserver.util import json_dump, parse_request, PYDANTIC_REQUEST_CONFIG

bp = MonitoredBlueprint('active_env_management', __name__)


class MakeEnvRequest(BaseModel):
    model_config = PYDANTIC_REQUEST_CONFIG

    env_class: str
    display_name: str
    config: Any
    display_group: str = ''    # Not used anymore, but kept for compatibility
    overwrite: bool = False


@bp.route('/makeenv/<env>', methods=['PUT'])
def makeenv(env: str):
    g.isJSON = True
    require_admin_auth()
    content = request.get_json()
    if not content:
        raise BadRequest('Expected JSON body')
    if not re.match('^[a-zA-Z0-9-.]+$', env):
        raise BadRequest(f'Illegal environment name {env!r}')

    request_data: MakeEnvRequest = parse_request(MakeEnvRequest, content)

    PluginManager.get(request_data.env_class)  # ensure that it exists

    ActiveEnvironment.new(
        identifier=env,
        env_class=request_data.env_class,
        display_name=request_data.display_name,
        display_group=request_data.display_group,
        config=json_dump(request_data.config),
        overwrite=request_data.overwrite,
    )

    return jsonify({'success': True})
