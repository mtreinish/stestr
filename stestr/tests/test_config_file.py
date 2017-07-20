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

import mock

from stestr import config_file
from stestr.tests import base


class TestTestrConf(base.TestCase):

    @mock.patch.object(config_file.configparser, 'ConfigParser')
    def setUp(self, mock_ConfigParser):
        super(TestTestrConf, self).setUp()
        self._testr_conf = config_file.TestrConf(mock.sentinel.config_file)
        self._testr_conf.parser = mock.Mock()

    @mock.patch.object(config_file.util, 'get_repo_open')
    @mock.patch.object(config_file.test_processor, 'TestProcessorFixture')
    @mock.patch.object(config_file, 'sys')
    def _check_get_run_command(self, mock_sys, mock_TestProcessorFixture,
                               mock_get_repo_open, platform='win32',
                               expected_python='python'):
        mock_sys.platform = platform

        fixture = self._testr_conf.get_run_command(test_path='fake_test_path',
                                                   top_dir='fake_top_dir',
                                                   group_regex='.*')

        self.assertEqual(mock_TestProcessorFixture.return_value, fixture)
        mock_get_repo_open.assert_called_once_with('file',
                                                   None)
        command = "%s -m subunit.run discover -t %s %s $LISTOPT $IDOPTION" % (
            expected_python, 'fake_top_dir', 'fake_test_path')
        # Ensure TestProcessorFixture is created with defaults except for where
        # we specfied and with the correct python.
        mock_TestProcessorFixture.assert_called_once_with(
            None, command, "--list", "--load-list $IDFILE",
            mock_get_repo_open.return_value, black_regex=None,
            blacklist_file=None, concurrency=0, group_callback=mock.ANY,
            test_filters=None, randomize=False, serial=False,
            whitelist_file=None, worker_path=None)

    def test_get_run_command_linux(self):
        self._check_get_run_command(platform='linux2',
                                    expected_python='${PYTHON:-python}')

    def test_get_run_command_win32(self):
        self._check_get_run_command()
