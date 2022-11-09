from __future__ import annotations

from aisysprojserver.env_interface import GenericEnvironment
from aisysprojserver.models import AgentDataModel


class AgentDataWrapper:
    def __init__(self, env: GenericEnvironment, model: AgentDataModel):
        self.env = env
        self.model: AgentDataModel = model

    @classmethod
    def new(cls, identifier: str, env_id: str, env: GenericEnvironment) -> AgentDataWrapper:
        return AgentDataWrapper(
            env,
            AgentDataModel(
                identifier=identifier,
                environment=env_id,
                recently_finished_runs='',
                recent_results='',
                rating=env.settings.INITIAL_RATING,
            )
        )

