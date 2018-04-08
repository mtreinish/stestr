# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import io
import os
import sys

import mock
import six

from stestr.tests import base
from stestr import user_config

FULL_YAML = """
run:
  concurrency: 42 # This can be any integer value
  random: True
  no-subunit-trace: True
  color: True
  abbreviate: True
  slowest: True
  suppress-attachments: True
failing:
  list: True
last:
  no-subunit-trace: True
  color: True
  suppress-attachments: True
load:
  force-init: True
  subunit-trace: True
  color: True
  abbreviate: True
  suppress-attachments: True
"""

INVALID_YAML_FIELD = """
run:
  color: True,
"""

YAML_NOT_INT = """
run:
  concurrency: Two
"""


class TestUserConfig(base.TestCase):

    def setUp(self):
        super(TestUserConfig, self).setUp()
        home_dir = os.path.expanduser("~")
        self.xdg_path = os.path.join(os.path.join(home_dir, '.config'),
                                     'stestr.yaml')
        self.home_path = os.path.join(home_dir, '.stestr.yaml')

    @mock.patch('sys.exit')
    @mock.patch('stestr.user_config.UserConfig')
    def test_get_user_config_invalid_path(self, user_mock, exit_mock):
        user_config.get_user_config('/i_am_an_invalid_path')
        exit_mock.assert_called_once_with(1)

    @mock.patch('os.path.isfile')
    @mock.patch('stestr.user_config.UserConfig')
    def test_get_user_config_xdg_file(self, user_mock, path_mock):

        def fake_isfile(path):
            if path == self.xdg_path:
                return True
            else:
                return False

        path_mock.side_effect = fake_isfile
        user_config.get_user_config()
        user_mock.assert_called_once_with(self.xdg_path)

    @mock.patch('os.path.isfile')
    @mock.patch('stestr.user_config.UserConfig')
    def test_get_default_user_config_file(self, user_mock, path_mock):

        def fake_isfile(path):
            if path == self.home_path:
                return True
            else:
                return False

        path_mock.side_effect = fake_isfile
        user_config.get_user_config()
        user_mock.assert_called_once_with(self.home_path)

    @mock.patch('yaml.load', return_value={})
    @mock.patch('six.moves.builtins.open', mock.mock_open())
    def test_user_config_empty_schema(self, yaml_mock):
        user_conf = user_config.UserConfig('/path')
        self.assertEqual({}, user_conf.config)

    def _restore_stdout(self, old_out):
        sys.stdout = old_out

    @mock.patch('yaml.load', return_value={'init': {'subunit-trace': True}})
    @mock.patch('sys.exit')
    @mock.patch('six.moves.builtins.open', mock.mock_open())
    def test_user_config_invalid_command(self, exit_mock, yaml_mock):

        temp_out = sys.stdout
        std_out = six.StringIO()
        sys.stdout = std_out
        self.addCleanup(self._restore_stdout, temp_out)
        user_config.UserConfig('/path')
        exit_mock.assert_called_once_with(1)
        error_string = ("Provided user config file /path is invalid because:\n"
                        "extra keys not allowed @ data['init']")
        std_out.seek(0)
        self.assertEqual(error_string, std_out.read().rstrip())

    @mock.patch('yaml.load', return_value={'run': {'subunit-trace': True}})
    @mock.patch('sys.exit')
    @mock.patch('six.moves.builtins.open', mock.mock_open())
    def test_user_config_invalid_option(self, exit_mock, yaml_mock):

        temp_out = sys.stdout
        std_out = six.StringIO()
        sys.stdout = std_out
        self.addCleanup(self._restore_stdout, temp_out)
        user_config.UserConfig('/path')
        exit_mock.assert_called_once_with(1)
        error_string = ("Provided user config file /path is invalid because:\n"
                        "extra keys not allowed @ "
                        "data['run']['subunit-trace']")
        std_out.seek(0)
        self.assertEqual(error_string, std_out.read().rstrip())

    @mock.patch('six.moves.builtins.open',
                return_value=io.BytesIO(FULL_YAML.encode('utf-8')))
    def test_user_config_full_config(self, open_mock):
        user_conf = user_config.UserConfig('/path')
        full_dict = {
            'run': {
                'concurrency': 42,
                'random': True,
                'no-subunit-trace': True,
                'color': True,
                'abbreviate': True,
                'slowest': True,
                'suppress-attachments': True},
            'failing': {
                'list': True},
            'last': {
                'no-subunit-trace': True,
                'color': True,
                'suppress-attachments': True},
            'load': {
                'force-init': True,
                'subunit-trace': True,
                'color': True,
                'abbreviate': True,
                'suppress-attachments': True}
        }
        self.assertEqual(full_dict, user_conf.config)

    @mock.patch('sys.exit')
    @mock.patch('six.moves.builtins.open',
                return_value=io.BytesIO(INVALID_YAML_FIELD.encode('utf-8')))
    def test_user_config_invalid_value_type(self, open_mock, exit_mock):
        temp_out = sys.stdout
        std_out = six.StringIO()
        sys.stdout = std_out
        self.addCleanup(self._restore_stdout, temp_out)
        user_config.UserConfig('/path')
        exit_mock.assert_called_once_with(1)
        error_string = ("Provided user config file /path is invalid because:\n"
                        "expected bool for dictionary value @ "
                        "data['run']['color']")
        std_out.seek(0)
        self.assertEqual(error_string, std_out.read().rstrip())

    @mock.patch('sys.exit')
    @mock.patch('six.moves.builtins.open',
                return_value=io.BytesIO(YAML_NOT_INT.encode('utf-8')))
    def test_user_config_invalid_integer(self, open_mock, exit_mock):
        temp_out = sys.stdout
        std_out = six.StringIO()
        sys.stdout = std_out
        self.addCleanup(self._restore_stdout, temp_out)
        user_config.UserConfig('/path')
        exit_mock.assert_called_once_with(1)
        error_string = ("Provided user config file /path is invalid because:\n"
                        "expected int for dictionary value @ "
                        "data['run']['concurrency']")
        std_out.seek(0)
        self.assertEqual(error_string, std_out.read().rstrip())
