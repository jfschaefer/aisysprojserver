import abc
import dataclasses
from typing import Optional, Any

from werkzeug.exceptions import NotFound


@dataclasses.dataclass(frozen=True)
class ActionResult:
    new_state: Optional[str] = None          # None means that the action was not accepted (e.g. invalid move)
    message: Optional[str] = None            # A message for the agent (considered an error message if new_state is None)
    action_extra_info: Optional[str] = None  # some sort of extra information related to the action (for action history)
    outcome: Optional[float] = None          # run is over if not None


@dataclasses.dataclass(frozen=True)
class ActionRequest:
    content: Any       # arbitrary JSON


@dataclasses.dataclass(frozen=True)
class ActionHistoryEntry:
    action: str
    extra_info: Optional[str]


@dataclasses.dataclass(frozen=True)
class RunData:
    action_history: list[ActionHistoryEntry]
    state: str
    outcome: Optional[float]


@dataclasses.dataclass(frozen=True)
class AbbreviatedRunData:
    run_id: str
    outcome: Optional[float]
    agent_name: str


@dataclasses.dataclass(frozen=True)
class AgentData:
    agent_name: str
    agent_rating: float
    recent_runs: list[AbbreviatedRunData]


@dataclasses.dataclass(frozen=True)
class EnvData:
    recent_runs: list[AbbreviatedRunData]
    agents: list[AgentData]


@dataclasses.dataclass(frozen=True)
class EnvInfo:
    display_name: str
    identifier: str

# THE REMAINDER IS IMPLEMENTED BY THE PLUGIN


class GenericEnvironment(abc.ABC):
    def __init__(self, env_info: EnvInfo, config_str: str):
        self.env_inf = env_info
        self.config_str = config_str

    def act(self, action: Any, run_data: RunData) -> ActionResult:  # invalid actions should be indicated in the return value (not via exceptions)
        raise NotImplementedError()

    def new_run(self) -> str:       # returns new state
        raise NotImplementedError()

    def get_action_request(self, run_data: RunData) -> ActionRequest:
        raise NotImplementedError()

    def view_run(self, run_data: RunData) -> str:
        raise NotFound(f'Viewing runs is not supported for this environment')

    def view_agent(self, agent_data: AgentData) -> str:       # idea: mixins for standard implementation
        raise NotFound(f'Viewing agents is not supported for this environment')

    def view_env(self, env_data: EnvData) -> str:
        raise NotImplementedError()
