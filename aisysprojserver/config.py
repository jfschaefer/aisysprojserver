from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from flask import current_app, Flask

registered_configs: dict[Flask, Config] = {}


def get() -> Config:
    return registered_configs[current_app]


class Config:
    CONFIG_NAME: str = 'test'

    MAX_CONTENT_LENGTH: int = 1000000  # respond 413 otherwise

    PERSISTENT: Path = Path('/tmp')

    @property
    def PLUGINS_DIR(self) -> Path:
        return self.PERSISTENT / 'plugins'

    # Logging etc.
    MIN_LOG_LEVEL = logging.INFO

    @property
    def LOG_FILE(self) -> Path:
        return self.PERSISTENT / 'aisysprojserver.log'

    PROMETHEUS_PORT: Optional[int] = 9464   # port on which Prometheus metrics are served (telemetry) - None to disable
    OTLP_ENDPOINT: Optional[str] = None  # OpenTelemetry collector endpoint - None to disable

    # Caching
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 5  # in seconds

    # database
    @property
    def DATABASE_URI(self) -> str:
        return f'sqlite:///{self.PERSISTENT.absolute()}/aisysprojserver.db'

    # admin access
    # Run ``authentication.py`` to generate a password and a hash
    ADMIN_AUTH = None  # the hash of the password (None means admin access is based on a file)

    def register(self, app: Flask):
        registered_configs[app] = self


class TestConfig(Config):
    # password for tests is 'test-admin-password'
    ADMIN_AUTH = 'sha256:f7a03f48c0e2aa2d5e55ca186c20032ddbf53b7f5f93fce387d65c3f83433e8d'


class UwsgiConfig(Config):
    ADMIN_AUTH = None
    CONFIG_NAME = 'uwsgi'
    PERSISTENT: Path = Path('/app/persistent')
    # PLUGINS_DIR: Path = Path('/app/persistent/plugins')
    # DATABASE_URI = 'sqlite:////app/persistent/aisysprojserver.db'
    # LOG_FILE = '/app/persistent/aisysprojserver.log'

    OTLP_ENDPOINT = 'http://localhost:4318/v1/metrics'
    PROMETHEUS_PORT = None   # multiple processes -> port conflict
