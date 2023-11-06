import copy
import logging

from aisysprojserver_test.servertestcase import ServerTestCase


def get_strong_nim_move(percept):
    return max((percept % 4), 1)


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

    def test_act_bad_username(self):
        self.require_standard_setup()
        config = copy.deepcopy(self._testuser_content)
        config['agent'] = 'wrongagent'
        self.assertEqual(self.act(config, 2, get_strong_nim_move), 401)

    def test_act_bad_password(self):
        self.require_standard_setup()
        config = copy.deepcopy(self._testuser_content)
        config['pwd'] = 'wrongpassword'
        self.assertEqual(self.act(config, 2, get_strong_nim_move), 401)
