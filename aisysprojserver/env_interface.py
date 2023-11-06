from __future__ import annotations

import abc
import dataclasses
from typing import Optional, Any

from werkzeug.exceptions import NotFound

from aisysprojserver.env_settings import EnvSettings


@dataclasses.dataclass(frozen=True)
class ActionResult:
    new_state: Optional[Any] = None         # None means that the action was not accepted (e.g. invalid move)
    message: Optional[str] = None           # A message for the agent (considered an error message if new_state is None)
    action_extra_info: Any = None           # some sort of extra information related to the action (for action history)
    outcome: Optional[Any] = None           # run is over if not None

    @classmethod
    def error(cls, message: str) -> ActionResult:
        return ActionResult(new_state=None, message=message)


@dataclasses.dataclass(frozen=True)
class ActionRequest:
    content: Any       # arbitrary JSON


@dataclasses.dataclass(frozen=True)
class ActionHistoryEntry:
    action: Any
    extra_info: Any


@dataclasses.dataclass(frozen=True)
class RunData:
    action_history: list[ActionHistoryEntry]
    state: Any
    outcome: Optional[Any]
    run_id: int
    agent_name: str


@dataclasses.dataclass(frozen=True)
class AbbreviatedRunData:
    run_id: int
    outcome: Optional[Any]
    agent_name: str


@dataclasses.dataclass(frozen=True)
class AgentDataSummary:
    agent_name: str
    agent_rating: float
    current_agent_rating: float
    recent_runs: list[AbbreviatedRunData]
    total_number_of_runs: int
    fully_evaluated: bool


@dataclasses.dataclass(frozen=True)
class EnvData:
    agents: list[AgentDataSummary]
    recent_runs: list[AbbreviatedRunData]


@dataclasses.dataclass(frozen=True)
class EnvInfo:
    display_name: str
    identifier: str

# THE REMAINDER IS IMPLEMENTED BY THE PLUGIN


class GenericEnvironment(abc.ABC):
    settings: EnvSettings = EnvSettings()

    def __init__(self, env_info: EnvInfo, config_json: Any):
        self.env_info: EnvInfo = env_info
        self.config_json = config_json

    def act(self, action: Any, run_data: RunData) -> ActionResult:
        # invalid actions should be indicated in the return value (not via exceptions)
        raise NotImplementedError()

    def new_run(self) -> Any:       # returns new state
        raise NotImplementedError()

    def get_action_request(self, run_data: RunData) -> ActionRequest:
        raise NotImplementedError()

    def view_run(self, run_data: RunData) -> str:
        raise NotFound('Viewing runs is not supported for this environment')

    def view_agent(self, agent_data: AgentDataSummary) -> str:       # idea: mixins for standard implementation
        raise NotFound('Viewing agents is not supported for this environment')

    def view_env(self, env_data: EnvData) -> str:
        raise NotImplementedError()
