from __future__ import annotations

import secrets
from enum import IntEnum
from typing import Optional, Callable

from flask import request
from werkzeug.exceptions import Unauthorized, BadRequest

from aisysprojserver.models import AgentAccountModel, Session, ModelMixin
from aisysprojserver.authentication import require_password_match, default_pwd_hash


class NoSuchAgentError(Exception):
    pass


class AgentStatus(IntEnum):
    LOCKED = 0
    ACTIVE = 1


class AgentAccount(ModelMixin[AgentAccountModel]):
    _authenticated: bool = False

    def __init__(self, environment: str, agentname: str, is_client: bool = False):
        ModelMixin.__init__(self, AgentAccountModel)
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
                raise BadRequest(f'No agent was specified')
            agent = content['agent']
            if not isinstance(agent, str):
                raise BadRequest(f'Bad value for field "agent"')
        else:
            if 'agent' in content:
                raise BadRequest(f'Did not expect an agent to be specified in the request body')
        account = AgentAccount(environment, agent, is_client=True)

        # try authentication
        if 'pwd' in content:
            pwd = content['pwd']
            if not isinstance(pwd, str):
                raise BadRequest(f'Bad value for field "pwd"')
            # if an authentication is provided, we require it to be correct
            # this means that later on we don't have to worry about retrieving the password from the request
            account.require_authenticated(pwd)

        return account

    def is_authenticated(self) -> bool:
        return self._authenticated

    def require_authenticated(self, password: Optional[str]):
        if self._authenticated:
            return

        if password is not None:
            require_password_match(password, self._require_model().password)
        else:
            raise Unauthorized(f'Agent requires authentication but no password was provided (this may be a server issue)')

    def is_active(self) -> bool:
        return self._require_model().status == AgentStatus.ACTIVE

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

        with Session() as session:
            ac = session.get(AgentAccountModel, self.identifier)
            if ac is not None:
                if not overwrite:
                    raise BadRequest(f'Agent {self.identifier} already exists')
                session.delete(ac)
            session.commit()

            ac = AgentAccountModel(identifier=self.identifier, environment=self.environment,
                                   password=default_pwd_hash(password), status=AgentStatus.ACTIVE)
            session.add(ac)
            session.commit()

        return password

    def block(self):
        def block(ac: AgentAccountModel):
            ac.status = AgentStatus.LOCKED
        self._change_model(block)

    def unblock(self):
        def unblock(ac: AgentAccountModel):
            ac.status = AgentStatus.ACTIVE
        self._change_model(unblock)
