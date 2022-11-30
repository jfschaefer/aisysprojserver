import json
import logging
from pathlib import Path
import random
from time import sleep

from aisysprojserver_clienttools.admin import AdminClient
from aisysprojserver_clienttools.client_simple import run
from aisysprojserver_clienttools.upload_plugin import upload_plugin

ac = AdminClient('http://localhost:5000', 'test-admin-password')

upload_plugin(ac, Path('example_envs/simple_nim'))
ac.make_env(env_class='simple_nim.environment:Environment', identifier='env1',
            display_name='Nim 1', display_group='Nim 2022')
ac.make_env(env_class='simple_nim.environment:Environment', identifier='env2',
            display_name='Nim 2', display_group='Nim 2022')
ac.make_env(env_class='simple_nim.environment:Environment', identifier='env3',
            display_name='Nim 1', display_group='Nim 2023')
ac.make_env(env_class='simple_nim.environment:Environment', identifier='env4',
            display_name='Nim 15', display_group='Nim 2023')

code, content = ac.new_user('env1', 'TestUserEnv1')
if code == 200:
    content['url'] = ac.base_url

    with open('/tmp/aisystestconfig.json', 'w') as fp:
        fp.write(json.dumps(content))
else:
    print(code, content)


def play(state):
    sleep(0.3)
    # action = random.randint(1, min(state, 3))
    action = max((state % 4), 1)
    return action

logging.basicConfig(level=logging.INFO)

run('/tmp/aisystestconfig.json', play)

