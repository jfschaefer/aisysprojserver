import random
from pathlib import Path
from typing import Any

import jinja2

from aisysprojserver.env_interface import GenericEnvironment, RunData, ActionResult, ActionRequest
from aisysprojserver.env_mixins import SimpleViewEnv, SimpleViewAgent
from aisysprojserver.env_settings import EnvSettings
from aisysprojserver.website import AISYSPROJ_TEMPLATES, TEMPLATE_STANDARD_KWARGS


class Environment(SimpleViewEnv, SimpleViewAgent, GenericEnvironment):
    settings = EnvSettings()
    settings.MIN_RUNS_FOR_FULLY_EVALUATED = 10
    settings.CAN_ABANDON_RUNS = True

    def act(self, action: Any, run_data: RunData) -> ActionResult:
        remaining = run_data.state['remaining']

        # error checking
        try:
            move = int(action)
        except ValueError:
            return ActionResult.error(f'Invalid action: {action!r}')
        except TypeError:
            return ActionResult.error(f'Invalid action (expected a string, got {action!r})')
        if move > 3 or move < 1:
            return ActionResult.error('You have to remove 1, 2, or 3 objects')
        if move > remaining:
            return ActionResult.error(f'You tried to take {move} objects, but only {remaining} are remaining')

        updated_state = remaining - move
        if updated_state == 0:  # victory
            return ActionResult(new_state={'remaining': 0, 'initial': run_data.state['initial']},
                                message='Congratulations, you won!', outcome=1)

        # environment/opponent makes an action
        if self.config_json['strong']:
            counter_action = updated_state % 4
            if not counter_action:  # cannot win -> random move
                counter_action = random.randint(1, 3)
        else:
            counter_action = random.randint(1, min(updated_state, 3))

        remaining = updated_state - counter_action
        return ActionResult(new_state={'remaining': remaining, 'initial': run_data.state['initial']},
                            message=f'Opponent removed {counter_action}' + (' – you lost.' if not remaining else ''),
                            action_extra_info=counter_action,
                            outcome=None if remaining else 0)

    def new_run(self):
        if self.config_json['random_start']:
            number = random.randint(9, 11)  # agent can always win
        else:
            number = 10
        return {'remaining': number, 'initial': number}

    def get_abandon_outcome(self, run_data: RunData) -> Any:
        return 0    # if a run is abandoned, the player loses

    def get_action_request(self, run_data: RunData) -> ActionRequest:
        return ActionRequest(content=run_data.state['remaining'])

    def view_run(self, run_data: RunData) -> str:
        jinja_environment = jinja2.Environment(
            loader=jinja2.FileSystemLoader([Path(__file__).parent / 'templates', AISYSPROJ_TEMPLATES]),
            autoescape=jinja2.select_autoescape(),
            trim_blocks=True
        )

        run_entries: list[str] = []
        remaining = run_data.state['initial']
        for entry in run_data.action_history:
            run_entries.append(f'Number of items: {remaining}, then '
                               f'you removed {entry.action}, then '
                               f'I removed {entry.extra_info}')
            remaining -= entry.action + (entry.extra_info or 0)
        return jinja_environment.get_template('nim_run.html').render(
            run_data=run_data,
            run_entries=run_entries,
            result={1: 'You won', 0: 'You lost', None: 'The game is still on-going'}[run_data.outcome],
            **TEMPLATE_STANDARD_KWARGS
        )
