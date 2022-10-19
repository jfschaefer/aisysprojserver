from __future__ import annotations

from typing import Optional, Callable

from werkzeug.exceptions import BadRequest

from aisysprojserver.env_interface import GenericEnvironment, EnvInfo
from aisysprojserver.models import ActiveEnvironmentModel, Session, ModelMixin
from aisysprojserver.plugins import PluginManager


class ActiveEnvironment(ModelMixin[ActiveEnvironmentModel]):

    def __init__(self, identifier: str):
        ModelMixin.__init__(self, ActiveEnvironmentModel)
        self.identifier = identifier

    @classmethod
    def new(cls, identifier: str, env_class: str, display_name: str, settings: str, overwrite: bool = False) -> ActiveEnvironment:
        if not isinstance(PluginManager.get(env_class), GenericEnvironment):
            raise BadRequest(f'{env_class} is not an instance of GenericEnvironment')
        with Session() as session:
            ae = session.get(ActiveEnvironmentModel, identifier)
            if ae is not None:
                if not overwrite:
                    raise BadRequest(f'Environment {identifier} already exists')
                session.delete(ae)
            session.commit()

            ae = ActiveEnvironmentModel(identifier=identifier,
                                        env_class=env_class,
                                        displayname=display_name,
                                        settings=settings,
                                        signup='restricted',
                                        status='active')

            session.add(ae)
            session.commit()

        return ActiveEnvironment(identifier)

    @property
    def display_name(self) -> str:
        return self._require_model().displayname

    @property
    def get_env_instance(self) -> GenericEnvironment:
        model = self._require_model()
        ge: type[GenericEnvironment] = PluginManager.get(model.env_class)
        return ge(EnvInfo(self.display_name, self.identifier), model.settings)
