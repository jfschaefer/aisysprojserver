import io
import logging
import sys
from pathlib import Path
from typing import Optional
from zipfile import ZipFile

from flask import Blueprint, request, g, jsonify

from aisysprojserver.authentication import require_admin_auth
logger = logging.Logger(__name__)


class BadPluginError(Exception):
    pass


class Plugin:
    package_name: str
    is_valid: bool = True

    def __init__(self, package_name: str):
        self.package_name = package_name

    def unimport(self):
        self.is_valid = False
        for module in list(sys.modules.keys()):
            if module == self.package_name or module.startswith(self.package_name + '.'):
                del sys.modules[module]


class PluginManager:
    # Note: the fact that there is a single PluginManager conflicts with the idea
    # that there can be multiple flask apps with different configs (and thus different plugins_dir's)
    plugins_dir: Optional[Path] = None
    plugins: dict[str, Plugin] = {}

    @classmethod
    @property
    def initialized(cls) -> bool:
        return cls.plugins_dir is not None

    @classmethod
    def init(cls, plugin_dir: Path):
        assert not cls.initialized, 'PluginManager should only be initialized once'
        cls.plugins_dir = plugin_dir
        sys.path.append(str(plugin_dir))
        cls._initialized = False

        for directory in plugin_dir.iterdir():
            if not directory.is_dir():
                logging.warning(f'{directory} does not seem to be a plugin directory')
            cls.plugins[directory.name] = Plugin(directory.name)
        logger.info(f'Successfully loaded the following plugins: ' + ', '.join(cls.plugins.keys()))

    @classmethod
    def load_from_zipfile(cls, zf: ZipFile):
        assert cls.initialized, 'PluginManager was not initialized'
        filenames = zf.namelist()
        if not filenames:
            raise BadPluginError('Empty plugin')
        package_name = filenames[0].split('/')[0]
        for filename in filenames:
            if not filename.startswith(package_name + '/') or filename == package_name:
                raise BadPluginError(f'Unexpected file {filename} in package {package_name}')
        if package_name in cls.plugins:
            cls.plugins[package_name].unimport()
        zf.extractall(cls.plugins_dir)
        print('asdf', cls.plugins_dir)
        cls.plugins[package_name] = Plugin(package_name)
        logger.info(f'Successfully loaded plugin {package_name}')


bp = Blueprint('plugins', __name__)


@bp.route('/uploadplugin', methods=['PUT'])
def upload():
    g.isJSON = True
    require_admin_auth()   # note: body is needed for plugin -> admin password must be passed via Authorization header
    data = request.get_data()
    with ZipFile(io.BytesIO(data)) as zf:
        PluginManager.load_from_zipfile(zf)

    return jsonify({'status': 'success'})
