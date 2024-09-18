from __future__ import annotations

import sqlalchemy

from aisysprojserver import models
from aisysprojserver.env_interface import AgentDataSummary
from aisysprojserver.run import Run
from aisysprojserver.util import json_load


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

        recent_runs = [Run(i).to_abbreviated_run_data() for i in json_load(str(m.recently_finished_runs))]

        return AgentDataSummary(
            agent_name=self.display_name,
            agent_rating=float(m.best_rating),
            current_agent_rating=float(m.current_rating),
            recent_runs=list(reversed(recent_runs)),
            total_number_of_runs=int(m.total_runs),
            fully_evaluated=bool(m.fully_evaluated),
        )

    def delete_nonrecent_runs(self, session=None):
        keep = [rr.run_id for rr in self.to_agent_data_summary().recent_runs]
        cmd = sqlalchemy.delete(models.RunModel).where(
            models.RunModel.agent == self.identifier,
            models.RunModel.finished == True,  # noqa: E712
            models.RunModel.identifier.not_in(keep),
        )
        if session:
            session.execute(cmd)
        else:
            with models.Session() as session:
                session.execute(cmd)
                session.commit()


def get_all_agentdata_for_env(env_id: str) -> list[AgentData]:
    with models.Session() as session:
        identifiers = session.execute(
            sqlalchemy.select(models.AgentDataModel.identifier).where(models.AgentDataModel.environment == env_id)
        )
        return [AgentData(identifier[0]) for identifier in identifiers]


def get_all_agentdata() -> list[AgentData]:
    with models.Session() as session:
        identifiers = session.execute(sqlalchemy.select(models.AgentDataModel.identifier))
        return [AgentData(identifier[0]) for identifier in identifiers]
