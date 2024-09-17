"""
To use this implementation, you simply have to implement `get_action` such that it returns a legal action.
You can then let your agent compete on the server by calling

    python3 client_simple_v1.py path/to/your/config.json
"""
import itertools
import json
import logging
import time

import requests


def get_action(percept):
    # TODO: return a move for the action request
    raise NotImplementedError()


def run(config_file, action_function, parallel_runs=True):
    logger = logging.getLogger(__name__)

    with open(config_file, 'r') as fp:
        config = json.load(fp)

    actions = []
    for request_number in itertools.count():
        logger.info(f'Iteration {request_number} (sending {len(actions)} actions)')
        # send request
        response = requests.put(f'{config["url"]}/act/{config["env"]}', json={
            'protocol_version': 1,
            'agent': config['agent'],
            'pwd': config['pwd'],
            'actions': actions,
            'parallel_runs': parallel_runs,
            'client': 'py-simple-client-v1',
        })
        if response.status_code == 200:
            response_json = response.json()
            for message in response_json['messages']:
                msg = f'Message from server: {message["content"]}'
                if message['type'] == 'error':
                    logger.error(msg)
                elif message['type'] == 'warning':
                    logger.warning(msg)
                else:
                    logger.info(msg)

            action_requests = response_json['action_requests']
            # get actions for next request
            actions = []
            for action_request in action_requests:
                actions.append({
                    'run': action_request['run'],
                    'act_no': action_request['act_no'],
                    'action': action_function(action_request['percept'])
                })
        elif response.status_code == 503:
            logger.warning('Server is busy - retrying in 3 seconds')
            time.sleep(3)  # server is busy - wait a moment and then try again
        else:
            # other errors (e.g. authentication problems) do not benefit from a retry
            logger.error(f'Status code {response.status_code}.')
            logger.error(f'Response: {response.text}')
            logger.error('Stopping.')
            break


if __name__ == '__main__':
    import sys
    run(sys.argv[1], get_action)
