from __future__ import annotations

import logging
from pathlib import Path

from flask import current_app, Flask

registered_configs: dict[Flask, Config] = {}


def get() -> Config:
    return registered_configs[current_app]


class Config:
    MAX_CONTENT_LENGTH: int = 1000000  # respond 413 otherwise

    PLUGINS_DIR: Path = Path('/tmp/plugins')  # directory for environment implementations etc.

    # Logging
    MIN_LOG_LEVEL = logging.INFO
    LOG_FILE = '/tmp/aisysprojserver.log'

    # Caching
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 5  # in seconds

    # database
    DATABASE_URI = 'sqlite:////tmp/aisysprojserver.db'

    # admin access
    # Run ``authentication.py`` to generate a password and a hash
    ADMIN_AUTH = ''  # the hash

    def register(self, app: Flask):
        registered_configs[app] = self


class TestConfig(Config):
    # password for tests is 'test-admin-password'
    ADMIN_AUTH = 'sha256:f7a03f48c0e2aa2d5e55ca186c20032ddbf53b7f5f93fce387d65c3f83433e8d'
