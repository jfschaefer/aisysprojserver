import json
import logging
import traceback
from pathlib import Path
from typing import Optional

from flask import Flask, g, jsonify
from werkzeug.exceptions import HTTPException, InternalServerError, Unauthorized

from aisysprojserver import models, agent_account_management, plugins, authentication, active_env_management, act, \
    website, admin
from aisysprojserver.config import Config, TestConfig
from aisysprojserver.plugins import PluginManager


def exception_handler(exception):
    if isinstance(exception, HTTPException):
        response = exception.get_response()
        if hasattr(g, 'isJSON') and g.isJSON:
            response.data = json.dumps({
                'errorcode': exception.code,
                'errorname': exception.name,
                'description': exception.description,
            })
            response.content_type = 'application/json'
        return response
    logger = logging.getLogger(__name__)
    logger.error('Unhandled exception', exc_info=exception)

    is_admin = False
    try:
        authentication.require_admin_auth()
        is_admin = True
    except Unauthorized:
        pass
    if is_admin:
        description = ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))
    else:
        # exception can leak sensitive data – don't forward them to non-admins
        description = type(exception).__name__

    admin.ERROR_BUFFER.append(''.join(traceback.format_exception(type(exception), exception, exception.__traceback__)))
    while len(admin.ERROR_BUFFER) > 50:
        admin.ERROR_BUFFER.pop(0)   # not exactly efficient, I think, but easy and not a problem

    if hasattr(g, 'isJSON') and g.isJSON:
        response = jsonify({'errorcode': 500, 'errorname': 'Internal Server Error',
                            'description': description})
        response.status_code = 500
        return response
    else:
        return InternalServerError(description).get_response()


def create_app(configuration: Optional[Config] = None) -> Flask:
    if not configuration:
        configuration = TestConfig()

    logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
                        filename=configuration.LOG_FILE,
                        level=configuration.MIN_LOG_LEVEL,
                        filemode='w')
    logging.info(f'Starting app with config {configuration.__class__.__name__}')

    if not PluginManager.initialized:
        if not (plugins_path := Path(configuration.PLUGINS_DIR)).is_dir():
            plugins_path.mkdir()
        logging.info(f'Loading plugins from {plugins_path}')
        PluginManager.set_plugins_dir(plugins_path)
        PluginManager.reload_all_plugins()

    models.setup(configuration)

    app = Flask(__name__)
    configuration.register(app)
    app.config.from_object(configuration)
    app.register_error_handler(Exception, exception_handler)
    app.register_blueprint(agent_account_management.bp)
    app.register_blueprint(active_env_management.bp)
    app.register_blueprint(plugins.bp)
    app.register_blueprint(act.bp)
    app.register_blueprint(website.bp)
    app.register_blueprint(admin.bp)
    website.cache.init_app(app)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run()
