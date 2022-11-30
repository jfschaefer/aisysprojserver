import dataclasses
import re
from typing import Any

from dataclasses_json import dataclass_json, Undefined
from flask import Blueprint, request, g, jsonify
from marshmallow import ValidationError
from werkzeug.exceptions import BadRequest

from aisysprojserver.active_env import ActiveEnvironment
from aisysprojserver.authentication import require_admin_auth
from aisysprojserver.json_util import json_dump
from aisysprojserver.plugins import PluginManager

bp = Blueprint('active_env_management', __name__)


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclasses.dataclass(frozen=True)
class MakeEnvRequest:
    env_class: str
    display_name: str
    display_group: str
    # TODO: Should be any, but that does not work because of https://github.com/lidatong/dataclasses-json/issues/292
    config: dict
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

    try:
        schema = MakeEnvRequest.schema()
        request_data: MakeEnvRequest = schema.load(content)
    except ValidationError as e:
        raise BadRequest('Bad JSON body: ' + repr(e.messages))

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
