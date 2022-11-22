import json
import logging
import time

from aisysprojserver_test.servertestcase import ServerTestCase


def get_strong_nim_move(percept):
    return min((percept % 4), 3)


class ActTest(ServerTestCase):
    def act(self, config, number_of_requests, action_function):
        logger = logging.getLogger(__name__)

        actions = []
        for request_number in range(number_of_requests):
            logger.debug(f'Iteration {request_number}')
            # send request
            logger.debug('Sending actions', actions)
            code, content = self.admin.send_request(f'/act/{config["env"]}', method='PUT', json={
                'agent': config['agent'],
                'pwd': config['pwd'],
                'actions': actions,
            })
            if code == 200:
                action_requests = content['action-requests']
                actions = []
                for action_request in action_requests:
                    actions.append({'run': action_request['run'], 'action': action_function(action_request['percept'])})
            else:
                return code

        return 200

    def test_act_simple(self):
        self.require_standard_setup()
        for i in range(5):
            self.assertEqual(self.act(self._testuser_content, 2, get_strong_nim_move), 200)