Server Protocol v0
==================

This document describes the server protocol version 0.
Note that there is a newer version with more features.

If you want to implement the client protocal, you might use the
`Simple Python client (v0) <https://github.com/jfschaefer/aisysprojserver/blob/main/aisysprojserver_clienttools/client_simple_v0.py>`_
implementation for reference.


Short summary
~~~~~~~~~~~~~

The client sends an HTTP request to the server with the credentials and actions,
and the server responds either with an error message or with a list of action requests
that the client should respond to in the next request.
For the first request, the client has to send an empty list of actions to get action requests
from the server.

Example interaction
~~~~~~~~~~~~~~~~~~~

The first request is a ``PUT`` request with an empty list of actions:

.. code-block:: python

   {"agent": "MyAgent", "pwd": "r7iUM8o1NLbFdkI2WmBDldsYHD3wLwUQAKoG_2_xBcE", "actions": []}

The server responds with a list of action requests:

.. code-block:: python


   {"errors": [], "messages": [], "action-requests": [
       {"run": "40#1", "percept": ...},
       {"run": "7#3", "percept": ...}]}

Now the client can send list of actions in the next request:

.. code-block:: python

   {"agent": "MyAgent", "pwd": "r7iUM8o1NLbFdkI2WmBDldsYHD3wLwUQAKoG_2_xBcE",
       "actions": [{"run": "40#1", "action": ...},
                   {"run": "7#3", "action": ...}]}

The request in detail
~~~~~~~~~~~~~~~~~~~~~

The agent config file (created by the server) contains the following fields:

- ``agent``: An identifier for the agent.
- ``env``: An identifier for the environment.
- ``pwd``: A password for the agent (note that the agent/password combination is specific to the environment).
- ``url``: The URL of the server.

The client should send the requests to ``[url]/act/[env]`` where ``[url]`` and ``[env]``
are the values from the agent config file.
The request body should contain a JSON object with the following fields:

- ``agent``: The agent identifier (as in the agent config file).
- ``pwd``: The agent password (as in the agent config file).
- ``actions``: A list of actions. Each action is a JSON object with two fields:
  ``run`` is an identifier of the action request (provided in the server responses)
  and ``action`` is the action to be performed -- the value format depends on the environment.
- ``single_request``: ``true`` or ``false``,
  indicating if only a single action request should be returned (can be used for debugging).
  In general, the server has multiple runs in parallel to speed up the process.

The server response
~~~~~~~~~~~~~~~~~~~

If the request was successful, you will receive a JSON object with the following fields:

- ``action-requests``: A list of action requests that you should send actions for.
  Each request is a JSON object with two fields:
  ``run`` is an identifier so that your action can be linked to the request,
  and ``percept`` describes what is known about the current state (e.g. the position in a game).
- ``errors``: A list of error messages.
- ``messages``: A list of other messages.

If the request was not successful, you will receive a JSON object with the following fields:

- ``errorcode``: The HTTP error code.
- ``errorname``: The HTTP error name.
- ``description``: A description of the error.

