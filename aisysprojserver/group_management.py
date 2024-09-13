import re

from flask import g, request, jsonify
from pydantic import BaseModel
from werkzeug.exceptions import BadRequest

from aisysprojserver.active_env import ActiveEnvironment
from aisysprojserver.authentication import require_admin_auth
from aisysprojserver.group import Group
from aisysprojserver.telemetry import MonitoredBlueprint
from aisysprojserver.util import parse_request, PYDANTIC_REQUEST_CONFIG

bp = MonitoredBlueprint('group_management', __name__)


class MakeGroupRequest(BaseModel):
    model_config = PYDANTIC_REQUEST_CONFIG

    title: str
    description: str
    overwrite: bool = False


@bp.route('/groupmanagement/make/<group>', methods=['PUT'])
def makegroup(group: str):
    g.isJSON = True
    require_admin_auth()
    content = request.get_json()
    if not content:
        raise BadRequest('Expected JSON body')
    if not re.match('^[a-zA-Z0-9-.]+$', group):
        raise BadRequest(f'Illegal group identifier {group.isidentifier()}')

    request_data: MakeGroupRequest = parse_request(MakeGroupRequest, content)

    Group.new(
        identifier=group,
        title=request_data.title,
        description=request_data.description,
        overwrite=request_data.overwrite,
    )

    return jsonify({'success': True})


@bp.route('/groupmanagement/delete/<group>', methods=['DELETE'])
def deletegroup(group: str):
    g.isJSON = True
    require_admin_auth()
    group_ = Group(group)
    if not group_.exists():
        raise BadRequest(f'No such group {group_.identifier}')
    group_.delete()
    return jsonify({'success': True})


@bp.route('/groupmanagement/addsubgroup/<group>/<subgroup>', methods=['PUT'])
def addsubgroup(group: str, subgroup: str):
    g.isJSON = True
    require_admin_auth()
    group_ = Group(group)
    subgroup_ = Group(subgroup)
    for g_ in [group_, subgroup_]:
        if not g_.exists():
            raise BadRequest(f'No such group {g_.identifier}')
    group_.add_subgroup(subgroup_)
    return jsonify({'success': True})


@bp.route('/groupmanagement/addenv/<group>/<env>', methods=['PUT'])
def addenv(group: str, env: str):
    g.isJSON = True
    require_admin_auth()
    group_ = Group(group)
    env_ = ActiveEnvironment(env)
    for model in [group_, env_]:
        if not model.exists():
            raise BadRequest(f'{model.identifier} does not exist')
    group_.add_env(env_)
    return jsonify({'success': True})
