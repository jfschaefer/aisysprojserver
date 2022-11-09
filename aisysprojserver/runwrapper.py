import json

from aisysprojserver.env_interface import GenericEnvironment
from aisysprojserver.models import RunModel


class RunWrapper:
    _authenticated: bool = False

    def __init__(self, env: GenericEnvironment, model: RunModel):
        self.env = env
        self.model = model

        self.history = json.loads(self.model.history or [])
