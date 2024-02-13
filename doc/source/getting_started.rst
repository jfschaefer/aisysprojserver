Getting Started
===============


Installation and running the server locally
-------------------------------------------

First, clone the repository. Then install the requirements using pip:

.. code-block:: bash

   $ python3 -m pip install -r requirements.txt

It might be easiest if you also install the aisysprojserver packages with pip
(the ``-e`` means that changes in the code are immediately available):

.. code-block:: bash

   $ python3 -m pip install -e .

Now you can run the server with

.. code-block:: bash

   $ python3 -m aisysprojserver.app

You should be able to see the server running at http://localhost:5000/.

.. important::

   When you start the server like that it's running in the test/debug/development mode.
   It is not safe to run it in production like that.

.. todo::

   Currently, configuration management is lacking.
   You can only change it by modifying ``config.py``.
   In particular, the development configuration uses UNIX paths and might
   not work on Windows.
   flask has good support for configuration files and we should start using it.


Uploading a plugin, making an environment and an agent, and running it
----------------------------------------------------------------------

Often, your code for the environment should not be public as it contains
a partial solution (think e.g. of the chess game where the environment
includes a strong opponent player).
Therefore, you can upload the relevant code as a plugin.
A plugin is simply a python package.
Re-uploading a plugin will overwrite the the previous version,
but depending on some technicalities, a restart of the server might be necessary.

You can use the client tools to upload a plugin:

>>> from aisysprojserver_clienttools.admin import AdminClient
>>> from aisysprojserver_clienttools.upload_plugin import upload_plugin
>>> # the password in the test configuration is 'test-admin-password'
>>> # (in some cases, you may have to use 127.0.0.1 instead of localhost)
>>> ac = AdminClient('http://localhost:5000', 'test-admin-password')
>>> plugin_path = 'example_envs/simple_nim/'   # example plugin in repository
>>> upload_plugin(ac, p)

Now, the ``simple_nim`` package should be available on the server
(of course you can also install the package conventionally using pip).
Next, we can make a new environment that uses the plugin and create a new agent for it:

>>> ac.make_env(env_class='simple_nim.environment:Environment',
...             identifer='test-nim',
...             display_name='Test Environment (Nim)',
...             display_group='Test Environments',
...             config={},
...             overwrite=False)
>>> _, content = ac.new_user(env='test-nim', user='test-user')
>>> # store the agent configuration in a file
>>> import json
>>> with open('agent_config.json', 'w') as fp:
...     json.dump(content, fp)

Now, we can implement a simple agent that plays the game and run it.

>>> def agent_function(state):
...     import random
...     action = random.randint(1, min(state, 3))
...     return action
>>> from aisysprojserver_clienttools.client_simple import run
>>> run('agent_config.json', agent_function)

This will keep running until you interrupt it (e.g. with Ctrl-C).
Check the web interface to see the results.
