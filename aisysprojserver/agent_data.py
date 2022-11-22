from __future__ import annotations

from typing import Optional

import sqlalchemy

from aisysprojserver import models
from aisysprojserver.env_interface import AgentDataSummary
from aisysprojserver.json_util import json_load
from aisysprojserver.run import Run


class AgentData(models.ModelMixin[models.AgentDataModel]):
    identifier: str

    def __init__(self, identifier):
        models.ModelMixin.__init__(self, models.AgentDataModel)
        self.identifier = identifier

    @property
    def display_name(self) -> str:
        return '/'.join(self.identifier.split('/')[1:])

    def to_agent_data_summary(self) -> AgentDataSummary:
        m = self._require_model()

        recent_runs = [Run(i).to_abbreviated_run_data() for i in json_load(m.recently_finished_runs)]

        return AgentDataSummary(
            agent_name=self.display_name,
            agent_rating=m.best_rating,
            current_agent_rating=m.current_rating,
            recent_runs=list(reversed(recent_runs)),
            total_number_of_runs=m.total_runs,
            fully_evaluated=m.fully_evaluated,
        )


def get_all_agentdata_for_env(env_id: str) -> list[AgentData]:
    with models.Session() as session:
        identifiers = session.execute(sqlalchemy.select(models.AgentDataModel.identifier).where(models.AgentDataModel.environment == env_id))
        return [AgentData(identifier[0]) for identifier in identifiers]

