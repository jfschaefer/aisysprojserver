Implementing a new environment type
===================================

To create a new environment type, you need to create a new class that inherits from the
:class:`~aisysprojserver.env_interface.GenericEnvironment` class.

An environment object has three separate configuration attributes:

* :attr:`~aisysprojserver.env_interface.GenericEnvironment.settings` is an class attribute. It should be an instance of
  :class:`~aisysprojserver.env_settings.EnvSettings`.
  It contains all kinds of attributes that are relevant for every environment instance
  of this type.
  For example, it can specify whether higher or lower ratings are better.
* :attr:`~aisysprojserver.env_interface.GenericEnvironment.env_info`
  contains general information about the environment instance:
  its identifier and its display name.
* :attr:`~aisysprojserver.env_interface.GenericEnvironment.config_json`
  contains arbitrary (JSON-based) configuration of the environment instance.
  For example, for a chess environment, it might contain the opponent strength
  or the color of the player (if it is not chosen randomly).

The environment class must implement the following methods:

* :meth:`~aisysprojserver.env_interface.GenericEnvironment.new_run`
  creates a new run.
  Concretely, it should return the state of the new run (JSON-based).
  For example, for a chess environment, it might return the initial board state.
* :meth:`~aisysprojserver.env_interface.GenericEnvironment.get_action_request`
  should return a new action request for a given run.
  It gets passed a :class:`~aisysprojserver.env_interface.RunData` object,
  which contains the history of the run so far, including the state.
  It should return a :class:`~aisysprojserver.env_interface.ActionRequest`,
  which contains the data that should be conveyed to the agent
  (it might be the state/sensor information/...).
* :meth:`~aisysprojserver.env_interface.GenericEnvironment.act`
  gets passed the action sent by the agent (arbitrary JSON) and
  a :class:`~aisysprojserver.env_interface.RunData` object.
  It should return a :class:`~aisysprojserver.env_interface.ActionResult`
  that might contain the new state, the outcome, or an error message.
* :meth:`~aisysprojserver.env_interface.GenericEnvironment.view_env`
  gets passed an :class:`~aisysprojserver.env_interface.EnvData` object
  containing some data about the agents and recent runs in the environment instance.
  It should return an HTML string that is displayed in the environment view.
  For example, it can contain a leader board.
  You can get a simple default implementation by also inheriting from
  :class:`~aisysprojserver.env_mixins.SimpleViewEnv`.
* :meth:`~aisysprojserver.env_interface.GenericEnvironment.view_agent`
  gets passed an :class:`~aisysprojserver.env_interface.AgentDataSummary` object
  containing some data about the agent.
  It should return an HTML string that is displayed when viewing the agent
  (e.g. its rating and its recent runs).
  If you do not implement it, viewing an agent is not possible.
  You can get a simple default implementation by also inheriting from
  :class:`~aisysprojserver.env_mixins.SimpleViewAgent`.
* :meth:`~aisysprojserver.env_interface.GenericEnvironment.view_run`
  gets passed a :class:`~aisysprojserver.env_interface.RunData` object
  containing some data about the run.
  It should return an HTML string that is displayed when viewing the run.
  For example, it can contain a visualization of the run (e.g. an animation of the chess game).
  If you do not implement it, viewing a run is not possible.
