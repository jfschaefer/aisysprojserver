import dataclasses
import random
from typing import Any

from dataclasses_json import dataclass_json

from aisysprojserver.env_interface import GenericEnvironment, RunData, ActionResult, EnvInfo, ActionRequest


@dataclass_json
@dataclasses.dataclass(frozen=True)
class Config:
    strong: bool = True
    random_start: bool = False


class Environment(GenericEnvironment):
    def __init__(self, env_info: EnvInfo, config_str: str):
        GenericEnvironment.__init__(self, env_info, config_str)

        self.config: Config = Config.schema().loads(config_str)

    def act(self, action: Any, run_data: RunData) -> ActionResult:
        state = int(run_data.state)

        # error checking
        try:
            move = int(action)
        except ValueError:
            return ActionResult(message=f'Invalid action: {action!r}')
        except TypeError:
            return ActionResult(message=f'Invalid action (expected a string, got {action!r})')
        if move > 3 or move < 1:
            return ActionResult(message=f'You have to remove 1, 2, or 3 objects')
        if move > state:
            return ActionResult(message=f'You tried to take {move} objects, but only {state} are remaining')

        updated_state = state - move
        if updated_state == 0:  # victory
            return ActionResult(new_state='0', message='Congratulations, you won!', outcome=1.0)

        # environment/opponent makes an action
        if self.config.strong:
            counter_action = updated_state % 4
            if not counter_action:       # cannot win -> random move
                counter_action = random.randint(1, 3)
        else:
            counter_action = random.randint(1, min(updated_state, 3))

        remaining = updated_state-counter_action
        return ActionResult(new_state=str(remaining),
                            message=f'Opponent removed {counter_action}' + (' – you lost.' if not remaining else ''),
                            action_extra_info=counter_action,
                            outcome=None if remaining else 0.0)

    def new_run(self) -> str:
        if self.config.random_start:
            return str(random.randint(9, 11))    # agent can always win
        else:
            return '10'

    def get_action_request(self, run_data: RunData) -> ActionRequest:
        return ActionRequest(content=int(run_data.state))
