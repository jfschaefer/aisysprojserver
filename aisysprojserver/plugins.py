import importlib
import io
import logging
import sys
from pathlib import Path
from typing import Optional
from zipfile import ZipFile

from flask import Blueprint, request, g, jsonify

from aisysprojserver.authentication import require_admin_auth
logger = logging.getLogger(__name__)


class BadPluginError(Exception):
    pass


class Plugin:
    package_name: str
    is_valid: bool = True
    _init_module = None

    def __init__(self, package_name: str):
        self.package_name = package_name

    def unimport(self):
        self.is_valid = False
        for module in list(sys.modules.keys()):
            if module == self.package_name or module.startswith(self.package_name + '.'):
                del sys.modules[module]

    @property
    def init_module(self):
        if not self._init_module:
            self._init_module = importlib.import_module(self.package_name)
        return self._init_module

    @property
    def version(self) -> Optional[str]:
        if hasattr(self.init_module, '__version__'):
            return self.init_module.__version__
        return None


class PluginManager:
    # Note: the fact that there is a single PluginManager conflicts with the idea
    # that there can be multiple flask apps with different configs (and thus different plugins_dir's).
    # It makes it a bit uglier, but isn't a problem because in practice.
    plugins_dir: Optional[Path] = None
    plugins: dict[str, Plugin] = {}

    @classmethod
    def set_plugins_dir(cls, plugins_dir: Path):
        assert cls.plugins_dir is None, 'plugins_dir already set'
        cls.plugins_dir = plugins_dir
        sys.path.append(str(plugins_dir))

    @classmethod
    @property
    def initialized(cls) -> bool:
        return cls.plugins_dir is not None

    @classmethod
    def reload_all_plugins(cls):
        if cls.plugins:
            logger.info('Unloading already loaded plugins')
            for plugin in cls.plugins.values():
                plugin.unimport()
            cls.plugins = {}

        for directory in cls.plugins_dir.iterdir():
            if not directory.is_dir():
                logging.warning(f'{directory} does not seem to be a plugin directory')
            cls.plugins[directory.name] = Plugin(directory.name)
        logger.info('Successfully loaded the following plugins: ' + ', '.join(cls.plugins.keys()))

    @classmethod
    def load_from_zipfile(cls, zf: ZipFile) -> str:
        logger.info('Trying to load plugin from zip file')
        filenames = zf.namelist()
        if not filenames:
            raise BadPluginError('Empty plugin')
        package_name = filenames[0].split('/')[0]
        for filename in filenames:
            if not filename.startswith(package_name + '/') or filename == package_name:
                raise BadPluginError(f'Unexpected file {filename} in package {package_name}')
        if package_name in cls.plugins:
            cls.plugins[package_name].unimport()
        logger.info(f'Extracting plugin {package_name}')
        zf.extractall(cls.plugins_dir)

        cls.reload_all_plugins()

        # getting the version requires importing the package, which could already raise certain exceptions
        # e.g. for missing dependencies (it would be harder to debug if they are raised later)
        version = cls.plugins[package_name].version
        logger.info(f'Successfully loaded plugin {package_name} version {version}')
        return package_name

    @classmethod
    def get(cls, reference: str):
        """ reference can be 'module.submodule' or 'module.submodule:attribute' """
        assert cls.initialized
        if ':' in reference:
            module, attribute = reference.split(':')
        else:
            module = reference
            attribute = None
        m = importlib.import_module(module)
        if not attribute:
            return m
        # if hasattr(m, attribute):  # it might be better have the error...
        return getattr(m, attribute)


bp = Blueprint('plugins', __name__)


@bp.route('/uploadplugin', methods=['PUT'])
def upload():
    g.isJSON = True
    require_admin_auth()   # note: body is needed for plugin -> admin password must be passed via Authorization header
    data = request.get_data()
    with ZipFile(io.BytesIO(data)) as zf:
        PluginManager.load_from_zipfile(zf)
    return jsonify({'status': 'success'})
