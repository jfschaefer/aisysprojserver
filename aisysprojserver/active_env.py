from __future__ import annotations

from werkzeug.exceptions import BadRequest

from aisysprojserver.env_interface import GenericEnvironment, EnvInfo
import aisysprojserver.models as models
from aisysprojserver.plugins import PluginManager


class ActiveEnvironment(models.ModelMixin[models.ActiveEnvironmentModel]):

    def __init__(self, identifier: str):
        models.ModelMixin.__init__(self, models.ActiveEnvironmentModel)
        self.identifier = identifier

    @classmethod
    def new(cls, identifier: str, env_class: str, display_name: str, config: str,
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
                                               config=config,
                                               signup='restricted',
                                               status='active')

            session.add(ae)
            session.commit()

        return ActiveEnvironment(identifier)

    @property
    def display_name(self) -> str:
        return self._require_model().displayname

    def get_env_instance(self) -> GenericEnvironment:
        model = self._require_model()
        ge: type[GenericEnvironment] = PluginManager.get(model.env_class)
        return ge(EnvInfo(self.display_name, self.identifier), model.config)
