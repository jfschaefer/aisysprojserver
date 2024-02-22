from __future__ import annotations

import sqlalchemy
from werkzeug.exceptions import BadRequest

from aisysprojserver import models
from aisysprojserver.active_env import ActiveEnvironment


class Group(models.ModelMixin[models.GroupModel]):
    def __init__(self, identifier: str):
        models.ModelMixin.__init__(self, models.GroupModel)
        self.identifier = identifier

    @classmethod
    def new(cls, identifier: str, title: str, description: str, overwrite: bool = False) -> Group:
        with models.Session() as session:
            group = session.get(models.GroupModel, identifier)
            if group is not None:
                if not overwrite:
                    raise BadRequest(f'Group {identifier} already exists')
                session.delete(group)
            group = models.GroupModel(identifier=identifier, displayname=title, description_html=description)
            session.add(group)
            session.commit()

        return Group(identifier)

    @property
    def display_name(self) -> str:
        return self._require_model().displayname

    @property
    def description(self) -> str:
        return self._require_model().description_html

    def get_envs(self) -> list[ActiveEnvironment]:
        with models.Session() as session:
            identifiers = session.execute(
                sqlalchemy.select(models.GroupEntryModel.entry).where(
                    models.GroupEntryModel.group == self.identifier,
                    models.GroupEntryModel.entry_type == 1
                )
            )
            return [ActiveEnvironment(identifier) for identifier in identifiers]

    def get_subgroups(self) -> list[Group]:
        with models.Session() as session:
            identifiers = session.execute(
                sqlalchemy.select(models.GroupEntryModel.entry).where(
                    models.GroupEntryModel.group == self.identifier,
                    models.GroupEntryModel.entry_type == 0
                )
            )
            return [Group(identifier) for identifier in identifiers]

    def add_env(self, env: ActiveEnvironment):
        with models.Session() as session:
            session.merge(models.GroupEntryModel(group=self.identifier, entry_type=1, entry=env.identifier))
            session.commit()

    def add_subgroup(self, subgroup: Group):
        with models.Session() as session:
            session.merge(models.GroupEntryModel(group=self.identifier, entry_type=0, entry=subgroup.identifier))
            session.commit()
