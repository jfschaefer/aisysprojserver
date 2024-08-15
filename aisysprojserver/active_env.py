from __future__ import annotations

import sqlalchemy
from werkzeug.exceptions import BadRequest

import aisysprojserver.models as models
from aisysprojserver.agent_data import get_all_agentdata_for_env
from aisysprojserver.env_interface import GenericEnvironment, EnvInfo, EnvData
from aisysprojserver.json_util import json_load
from aisysprojserver.plugins import PluginManager
from aisysprojserver.run import Run


class ActiveEnvironment(models.ModelMixin[models.ActiveEnvironmentModel]):
    def __init__(self, identifier: str):
        models.ModelMixin.__init__(self, models.ActiveEnvironmentModel)
        self.identifier = identifier

    @classmethod
    def new(cls, identifier: str, env_class: str, display_name: str, display_group: str, config: str,
            overwrite: bool = False) -> ActiveEnvironment:
        if not issubclass(PluginManager.get(env_class), GenericEnvironment):
            raise BadRequest(f'{env_class} is not a subclass of GenericEnvironment')
        with models.Session() as session:
            ae = session.get(models.ActiveEnvironmentModel, identifier)
            if ae is not None:
                if not overwrite:
                    raise BadRequest(f'Environment {identifier} already exists')
                session.delete(ae)
            session.commit()

            ae = models.ActiveEnvironmentModel(identifier=identifier,
                                               env_class=env_class,
                                               displayname=display_name,
                                               displaygroup=display_group,
                                               config=config,
                                               signup='restricted',
                                               status='active')

            session.add(ae)
            session.commit()

        return ActiveEnvironment(identifier)

    @property
    def display_name(self) -> str:
        return self._require_model().displayname

    @property
    def display_group(self) -> str:
        return self._require_model().displaygroup

    @property
    def env_class_refstr(self) -> str:
        return self._require_model().env_class

    @property
    def recent_runs_key(self) -> str:
        return self.identifier + '#recentruns'

    def get_env_instance(self) -> GenericEnvironment:
        model = self._require_model()
        ge: type[GenericEnvironment] = PluginManager.get(model.env_class)

        return ge(EnvInfo(self.display_name, self.identifier),
                  json_load(model.config))

    def get_env_data(self) -> EnvData:
        with models.Session() as session:
            kva = models.KeyValAccess(session)
            run_ids = json_load(kva[self.recent_runs_key] or '[]')
        runs = [Run(i).to_abbreviated_run_data() for i in run_ids]

        return EnvData(
            agents=[ad.to_agent_data_summary() for ad in get_all_agentdata_for_env(self.identifier)],
            recent_runs=runs,
        )


def get_all_active_envs() -> list[ActiveEnvironment]:
    with models.Session() as session:
        identifiers = session.execute(sqlalchemy.select(models.ActiveEnvironmentModel.identifier))
        return [ActiveEnvironment(identifier[0]) for identifier in identifiers]
