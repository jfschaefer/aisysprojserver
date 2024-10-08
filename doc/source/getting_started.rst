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


Using docker
~~~~~~~~~~~~

There is a docker image `jfschaefer/gs <https://hub.docker.com/r/jfschaefer/gs>`_ for the server.
After installing docker, you can run it with:

.. code-block:: bash

    $ sudo docker run -v /tmp/persistent:/app/persistent -p 80:80 jfschaefer/gs

This will run the server on port 80.
The persistent data (e.g. the database) is stored in the directory ``/tmp/persistent``, but you can change that.


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
>>> # the password in the test configuration is 'test-admin-password'
>>> # (in some cases, you may have to use 127.0.0.1 instead of localhost)
>>> ac = AdminClient('http://localhost:5000', 'test-admin-password')
>>> plugin_path = 'example_envs/simple_nim/'   # example plugin in repository
>>> ac.upload_plugin(plugin_path)

Now, the ``simple_nim`` package should be available on the server
(of course you can also install the package conventionally using pip).
Next, we can make a new environment that uses the plugin:

>>> ac.make_env(env_class='simple_nim.environment:Environment',
...             identifier='test-nim',
...             display_name='Test Environment (Nim)',
...             config={'strong': True, 'random_start': True},
...             overwrite=False)

You should be able to see the new environment in the web interface at
``http://localhost:5000/env/test-nim``.
Next, we will make a new user (agent) and create a configuration file for it:

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


Groups
------

So far, we have used a special URL to see the environment.
To make the page navigable, the server supports groups.
A group consists of:

* an identifier
* a title
* a description
* a list of links to environments (can be empty)
* a list of links to other groups (can be empty)

Let us make one and add the environment to it:

>>> ac.make_group(
...     identifier='nim-group',
...     title='Nim Group',
...     description='A group with all the Nim environments',
... )
>>> ac.add_env_to_group('nim-group', 'test-nim')

We can now see the group at ``http://localhost:5000/group/nim-group``.
The front page (``http://localhost:5000/``) will also show the group
``main``, which is automatically created.
Let us add the new group to the main group:

>>> ac.add_subgroup_to_group('main', 'nim-group')
