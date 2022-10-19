import json
import logging
import traceback
from pathlib import Path
from typing import Optional

from flask import Flask, g, jsonify
from werkzeug.exceptions import HTTPException, InternalServerError, Unauthorized

from aisysprojserver import models, agent_account_management, plugins, authentication
from aisysprojserver.config import Config
from aisysprojserver.plugins import PluginManager


def http_exception_handler(exception):
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
        description = '\n\n'.join(traceback.format_tb(exception.__traceback__))
    else:
        # exception can leak sensitive data – don't forward them to non-admins
        description = type(exception).__name__
    if hasattr(g, 'isJSON') and g.isJSON:
        response = jsonify({'errorcode': 500, 'errorname': 'Internal Server Error',
                            'description': description})
        response.status_code = 500
        return response
    else:
        return InternalServerError(description).get_response()


def create_app(configuration: Optional[Config]) -> Flask:
    if not configuration:
        configuration = Config()

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
    app.register_error_handler(Exception, http_exception_handler)
    app.register_blueprint(agent_account_management.bp)
    app.register_blueprint(plugins.bp)

    return app

