"""
    To use this implementation, you simply have to implement `get_action` such that it returns a legal action.
    You can then let your agent compete on the server by calling
        python3 client_simple.py path/to/your/config.json
"""
import itertools
import json
import logging
import math

import requests
import time


def get_action(percept):
    # TODO: return a move for the action request
    raise NotImplementedError()


def run(config_file, action_function, single_request=False):
    logger = logging.getLogger(__name__)

    with open(config_file, 'r') as fp:
        config = json.load(fp)

    actions = []
    for request_number in itertools.count():
        logger.info(f'Iteration {request_number}')
        # send request
        logger.info('Sending actions', actions)
        response = requests.put(f'{config["url"]}/act/{config["env"]}', json={
            'agent': config['agent'],
            'pwd': config['pwd'],
            'actions': actions,
            'single-request': single_request,
        })
        logger.info('Response status:', response.status_code)
        logger.info('Response text:', response.text)
        if response.status_code == 200:
            action_requests = response.json()['action-requests']
            if not action_requests:
                logger.info('The server has no new action requests - waiting for 1 second.')
                time.sleep(1)  # wait a moment to avoid overloading the server and then try again
            # get actions for next request
            actions = []
            for action_request in action_requests:
                actions.append({'run': action_request['run'], 'action': action_function(action_request['percept'])})
        elif response.status_code == 503:
            logger.warning('Server is busy - retrying in 3 seconds')
            time.sleep(3)  # server is busy - wait a moment and then try again
        else:
            # other errors (e.g. authentication problems) do not benefit from a retry
            logger.error(f'Status code {response.status_code}. Stopping.')
            break


if __name__ == '__main__':
    import sys
    run(sys.argv[1], get_action)
