import base64
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class AdminClient:
    def __init__(self, url: str, password: str):
        self.base_url = url
        self.pwd = password

    def send_request(self, path: str, **kwargs) -> tuple[int, Any]:
        """ Overwritten for integration tests """
        response = requests.request(url=self.base_url + path, **kwargs)
        response_log_level: int = logging.DEBUG
        if response.status_code not in {200, 201}:
            response_log_level = logging.ERROR
        logger.log(response_log_level, f'Got a {response.status_code} response with content: {response.text}')
        return response.status_code, response.json()

