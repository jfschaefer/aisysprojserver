import logging

from aisysprojserver import telemetry
from aisysprojserver.app import create_app
from aisysprojserver.config import UwsgiConfig

from uwsgidecorators import postfork  # type: ignore

config = UwsgiConfig()
app = create_app(config)


@postfork
def setup_telemetry():
    logging.info('Setting up telemetry (uwsgi postfork)')
    telemetry.setup(config)
