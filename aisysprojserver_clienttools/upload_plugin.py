import base64
import io
import logging
from pathlib import Path
from zipfile import ZipFile

from aisysprojserver_clienttools.admin import AdminClient

logger = logging.getLogger(__name__)


def upload_plugin(client: AdminClient, package: Path | str):
    assert package.is_dir()

    package = Path(package)

    data = io.BytesIO()
    with ZipFile(data, 'w') as zf:
        for file_path in package.rglob("*"):
            rel_path = file_path.relative_to(package.parent)
            if '__pycache__' in str(rel_path):
                continue
            logger.debug(f'Including {rel_path}')
            zf.write(file_path, arcname=rel_path)

    encoded_pwd = (
        base64.
        encodebytes(client.pwd.encode())
        .decode()
        .replace('\n', '')   # no linebreaks in header
    )
    return client.send_request('/uploadplugin', method='PUT', data=data.getvalue(),
                               headers={'Authorization': f'Basic {encoded_pwd}'})
