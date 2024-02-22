import logging
import warnings
from pathlib import Path

from aisysprojserver_clienttools.admin import AdminClient

logger = logging.getLogger(__name__)


def upload_plugin(client: AdminClient, package: Path | str):
    warnings.warn('This function is deprecated and will be removed in a future version. '
                  'Use AdminClient.upload_plugin instead', DeprecationWarning)
    return client.upload_plugin(package)
