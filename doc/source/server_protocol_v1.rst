Server Protocol v1
==================

This document describes the server protocol version 1.

If you want to implement the client protocal, you might use the
`Simple Python client (v1) <https://github.com/jfschaefer/aisysprojserver/blob/main/aisysprojserver_clienttools/client_simple_v1.py>`_
implementation for reference.


Short summary
~~~~~~~~~~~~~

The client sends an HTTP request to the server with the credentials and actions,
and the server responds either with an error message or with a list of action requests
that the client should respond to in the next request.
For the first request, the client has to send an empty list of actions to get action requests
from the server.

Minimal example interaction
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first request is a ``GET`` or ``PUT`` with your agent credentials:

.. code-block:: python

    {
        "protocol_version": 1,
        "agent": "MyAgent",
        "pwd": "r7iUM8o1NLbFdkI2WmBDldsYHD3wLwUQAKoG_2_xBcE"
    }

The server responds with a list of action requests:

.. code-block:: python

    {
        "action_requests": [
            {"run": "7", "act_no": 3, "percept": ...},
            {"run": "40", "act_no": 1, "percept": ...}
        ],
        "active_runs": ["7", "40"],
        "messages": [],
        "finished_runs": [],
    }

Now the client can send list of actions in the next request:

.. code-block:: python

    {
        "protocol_version": 1,
        "agent": "MyAgent",
        "pwd": "r7iUM8o1NLbFdkI2WmBDldsYHD3wLwUQAKoG_2_xBcE",
        "actions": [
            {"run": "7", "act_no": 3, "action": ...},
            {"run": "40", "act_no": 1, "action": ...}
        ]
    }


The request in detail
~~~~~~~~~~~~~~~~~~~~~

The agent config file (created by the server) contains the following fields:

- ``protocol_version``: The protocol version used by the client.
  (should be 1 for this document).
- ``agent``: An identifier for the agent.
- ``env``: An identifier for the environment.
- ``pwd``: A password for the agent (note that the agent/password combination is specific to the environment).
- ``url``: The URL of the server.

The client should send the requests to ``[url]/act/[env]`` where ``[url]`` and ``[env]``
are the values from the agent config file.
The request body should contain a JSON object with the following fields:

- ``agent``: The agent identifier (as in the agent config file).
- ``pwd``: The agent password (as in the agent config file).
- ``actions``: A list of actions. Each action is a JSON object with three fields:

  - ``run`` is an identifier (string) of the run,
  - ``act_no`` is the number (integer) of the action in the run, and
  - ``action`` is the action to be performed -- the value format depends on the environment.

  You will receive the run identifiers action numbers from the server responses.
  For the first request, the client cannot know about the runs and requested actions,
  so it should skip the ``actions`` field or send an empty list.
- ``parallel_runs`` (optional): ``true`` or ``false``,
  indicating if the server should respond with multiple action requests.
  This can speed up the process as it reduces the number of requests necessary
  to evaluate your agent and allows for parallel processing of the requests.
  But for debugging, you might want to set this to ``false`` to finish one run before starting the next.
  The default is ``true``.
- ``to_abandon`` (optional): A list of identifiers of runs that should be abandoned.
  This can be used if your agent is stuck in a run or if you want to test a new version of your agent
  without waiting for the old runs to finish.
  The abandoned runs will be marked as "lost", i.e. they will get the worst possible score.
  Note that not all environments support abandoning runs.
- ``client`` (optional): A string that identifies the client implementation.


The server response
~~~~~~~~~~~~~~~~~~~


If the request was successful, you will receive a JSON object with the following fields:

- ``action_requests``: A list of action requests that you should send actions for.
  Each request is a JSON object with three fields:

  - ``run`` is an identifier of the run (string),
  - ``act_no`` is the number of the action in the run (integer), and
  - ``percept`` describes what is known about the current state (e.g. the position in a game).

- ``active_runs``: A list of identifiers of runs that are still active.
- ``messages``: A list of other messages.
  Each message is a JSON object with the following fields:

  - ``type`` is a string that describes the message type (``"info"``, ``"warning"``, ``"error"``).
  - ``content`` is a string with the actual message.
  - ``run`` is an identifier of the run that the message is related to (or ``null`` if it is not related to a specific run).

- ``finished_runs``: A JSON dictionary with one entry for each run that was finished with the previous request.
  The keys are the run identifiers and the values contain the outcome (format depends on the environment).
  Note that it is possible that your client never receives this information for some runs
  (e.g.\ if the client gets disconnected).


Error responses
~~~~~~~~~~~~~~~

If the request was unsuccessful, you will receive a JSON object with the following fields:

- ``errorcode``: The HTTP error code.
- ``errorname``: The HTTP error name.
- ``description``: A description of the error.

``500`` errors are internal server errors and should be reported.
The most common cause are bad actions (e.g. invalid moves) that are not handled correctly by
the plugin for the environment.
In this case you can avoid them by fixing your agent,
but you should still report the error to the server admin as the plugin should handle bad actions gracefully.
