from __future__ import annotations

from typing import Any

from aisysprojserver import models
from aisysprojserver.env_interface import AbbreviatedRunData, RunData, ActionHistoryEntry
from aisysprojserver.util import json_load


class Run(models.ModelMixin[models.RunModel]):
    identifier: int

    def __init__(self, identifier):
        models.ModelMixin.__init__(self, models.RunModel)
        self.identifier = identifier

    def get_history(self) -> list[str]:
        return json_load(str(self._require_model().history))

    def get_state(self) -> Any:
        return json_load(str(self._require_model().state))

    def to_abbreviated_run_data(self) -> AbbreviatedRunData:
        return AbbreviatedRunData(
            run_id=self.identifier,
            outcome=json_load(str(self._require_model().outcome)),
            agent_name=str(self._require_model().agent),
        )

    def to_run_data(self) -> RunData:
        history = json_load(str(self._require_model().history))
        return RunData(
            action_history=[ActionHistoryEntry(action, extra) for action, extra in history],
            state=json_load(str(self._require_model().state)),
            outcome=json_load(str(self._require_model().outcome)),
            agent_name='/'.join(self._require_model().agent.split('/')[1:]),
            run_id=self.identifier,
        )

    def env_str(self) -> str:
        return str(self._require_model().environment)


if __name__ == '__main__':
    raise Exception('This module is not the entry point for the server - use app.py or uwsgi_main.py instead')
