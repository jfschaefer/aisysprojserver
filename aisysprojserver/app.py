import json
import logging
from pathlib import Path
from typing import Optional

from flask import Flask, g, jsonify
from werkzeug.exceptions import HTTPException, InternalServerError

from aisysprojserver import models, agent_account_management, plugins
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
    if hasattr(g, 'isJSON') and g.isJSON:
        response = jsonify({'errorcode': 500, 'errorname': 'Internal Server Error',
                            'description': type(exception).__name__})
        response.status_code = 500
        return response
    else:
        return InternalServerError(type(exception).__name__).get_response()


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
        PluginManager.init(plugins_path)

    models.setup(configuration)

    app = Flask(__name__)
    configuration.register(app)
    app.config.from_object(configuration)
    app.register_error_handler(Exception, http_exception_handler)
    app.register_blueprint(agent_account_management.bp)
    app.register_blueprint(plugins.bp)

    return app

