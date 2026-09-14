import abc
import io
import json
import shutil
from pathlib import Path
from zipfile import ZipFile

from flask import g, request, jsonify
from werkzeug.exceptions import BadRequest, NotFound

from aisysprojserver import models
from aisysprojserver.authentication import require_admin_auth
from aisysprojserver.plugins import PluginManager
from aisysprojserver.telemetry import MonitoredBlueprint

bp = MonitoredBlueprint('verify', __name__)


class Verifier(abc.ABC):
    # could use a function, but we might want more attributes etc. in the future...
    @abc.abstractmethod
    def verify(self, data: bytes, data_path: Path) -> str | dict:
        raise NotImplementedError()


class VerifyConfig:
    """ Initialized during app setup """
    verify_path: Path


@bp.route('/verify/<identifier>', methods=['GET'])
def verify(identifier: str):
    g.isJSON = True

    with models.Session() as session:
        kva = models.KeyValAccess(session)
        verifier_path = kva[f'{identifier}#verifier']
        if verifier_path is None:
            raise NotFound(f'Verification system {identifier!r} not found')

    verifier = PluginManager.get(verifier_path)
    assert isinstance(verifier, Verifier)

    data = verifier.verify(
        request.get_data(),
        data_path=VerifyConfig.verify_path / identifier,
    )

    return data


@bp.route('/verify/<identifier>', methods=['PUT'])
def create_verify(identifier: str):
    g.isJSON = True
    require_admin_auth()   # note: body is needed for zip data -> admin password must be passed via Authorization header
    data = request.get_data()
    with ZipFile(io.BytesIO(data)) as zf:
        with zf.open('meta.json') as f:
            meta = json.load(f)

        if meta['identifier'] != identifier:  # sanity check
            raise BadRequest(f'Identifiers do not match ({meta['identifier']!r} != {identifier!r})')

        verifier = meta['verifier']
        path = VerifyConfig.verify_path / identifier
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
        zf.extractall(path)

        with models.Session() as session:
            # for now just using key value DB - TODO: make a new SQL table for this
            kva = models.KeyValAccess(session)
            kva[f'{identifier}#verifier'] = verifier
            session.commit()

    return jsonify({'status': 'success'})


@bp.route('/verify/<identifier>', methods=['DELETE'])
def delete_verify(identifier: str):
    path = VerifyConfig.verify_path / identifier
    path.unlink()  # delete
    with models.Session() as session:
        kva = models.KeyValAccess(session)
        del kva[f'{identifier}#verifier']
        session.commit()

    return jsonify({'status': 'success'})
