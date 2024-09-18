import copy
import logging

from aisysprojserver_test.servertestcase import ServerTestCase, get_strong_nim_move


class ActTest(ServerTestCase):
    def act(self, config, number_of_requests, action_function, protocol_version=1):
        assert protocol_version in {0, 1}
        logger = logging.getLogger(__name__)

        actions: list = []
        for request_number in range(number_of_requests):
            logger.debug(f'Iteration {request_number}')
            # send request
            logger.debug('Sending actions', actions)
            request_content = {
                'agent': config['agent'],
                'pwd': config['pwd'],
                'actions': actions,
            }
            if protocol_version == 1:
                request_content['protocol_version'] = 1
            code, content = self.admin.send_request(f'/act/{config["env"]}', method='PUT', json=request_content)
            if code == 200:
                action_requests = content['action-requests' if protocol_version == 0 else 'action_requests']
                actions = []
                for action_request in action_requests:
                    action_json = {
                        'run': action_request['run'],
                        'action': action_function(action_request['percept'])
                    }
                    if protocol_version == 1:
                        action_json['act_no'] = action_request['act_no']
                    actions.append(action_json)
            else:
                return code

        return 200

    def test_act_simple(self):
        self.require_standard_setup()
        for i in range(5):
            self.assertEqual(
                self.act(self._testuser_content, 2, get_strong_nim_move, protocol_version=i % 2),
                200
            )

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
