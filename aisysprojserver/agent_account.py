from __future__ import annotations

import secrets
from enum import IntEnum
from typing import Optional

import sqlalchemy
from flask import request
from werkzeug.exceptions import Unauthorized, BadRequest

from aisysprojserver.authentication import require_password_match, default_pwd_hash
import aisysprojserver.models as models


class NoSuchAgentError(Exception):
    pass


class AgentStatus(IntEnum):
    LOCKED = 0
    ACTIVE = 1


class AgentAccount(models.ModelMixin[models.AgentAccountModel]):
    _authenticated: bool = False

    def __init__(self, environment: str, agentname: str, is_client: bool = False):
        models.ModelMixin.__init__(self, models.AgentAccountModel)
        self.environment = environment
        self.agentname = agentname
        self.is_client = is_client    # indicates that the client is making the request (helps with error messages)
        self.identifier = f'{self.environment}/{self.agentname}'

    @classmethod
    def from_request(cls, environment: str, agent: Optional[str] = None) -> AgentAccount:
        content = request.get_json()
        if not content:
            raise BadRequest('Expected JSON body')
        if agent is None:
            if 'agent' not in content:
                raise BadRequest('No agent was specified')
            agent = content['agent']
            if not isinstance(agent, str):
                raise BadRequest('Bad value for field "agent"')
        else:
            if 'agent' in content:
                raise BadRequest('Did not expect an agent to be specified in the request body')
        account = AgentAccount(environment, agent, is_client=True)

        if not account.exists():
            raise Unauthorized(description='unknown agent')

        # try authentication
        if 'pwd' in content:
            pwd = content['pwd']
            if not isinstance(pwd, str):
                raise BadRequest('Bad value for field "pwd"')

            # if an authentication is provided, we require it to be correct
            # this means that later on we don't have to worry about retrieving the password from the request
            require_password_match(pwd, str(account._require_model().password))
            account._authenticated = True

        return account

    def is_authenticated(self) -> bool:
        return self._authenticated

    def require_authenticated(self):
        if not self._authenticated:
            raise Unauthorized(
                'Agent requires authentication but no password was provided (this may be a server issue)'
            )

    def is_active(self) -> bool:
        return int(self._require_model().status) == AgentStatus.ACTIVE

    def require_active(self):
        if not self.is_active():
            if self.is_client:
                raise Unauthorized(description='the agent is not active')
            else:
                raise AssertionError('the agent is not active')

    def signup(self, overwrite: bool = False) -> str:
        """ The caller must have verified that the environment and agentname are valid. Returns the password. """

        # password should always be server-generated to ensure it has enough entropy for efficient (unsafe) hashing
        password = secrets.token_urlsafe(32)

        with models.Session() as session:
            ac = session.get(models.AgentAccountModel, self.identifier)
            if ac is not None:
                if not overwrite:
                    raise BadRequest(f'Agent {self.identifier} already exists')
                session.delete(ac)
            session.commit()

            ac = models.AgentAccountModel(identifier=self.identifier, environment=self.environment,
                                          password=default_pwd_hash(password), status=AgentStatus.ACTIVE)
            session.add(ac)
            session.commit()

        return password

    def block(self):
        def block(ac: models.AgentAccountModel):
            ac.status = AgentStatus.LOCKED  # type: ignore
        self._change_model(block)

    def unblock(self):
        def unblock(ac: models.AgentAccountModel):
            ac.status = AgentStatus.ACTIVE  # type: ignore
        self._change_model(unblock)

    def delete(self):
        print(f'Deleting agent {self.identifier}')
        cmd = sqlalchemy.delete(models.AgentAccountModel).where(models.AgentAccountModel.identifier == self.identifier)
        with models.Session() as session:
            session.execute(cmd)
            session.commit()


def get_all_agentaccounts_for_env(env_id: str) -> list[AgentAccount]:
    with models.Session() as session:
        identifiers = session.execute(
            sqlalchemy.select(models.AgentAccountModel.identifier).where(models.AgentAccountModel.environment == env_id)
        )
        return [AgentAccount(env_id, identifier[0][len(env_id) + 1:]) for identifier in identifiers]
