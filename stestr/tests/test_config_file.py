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

from unittest import mock

import ddt

from stestr import config_file
from stestr.tests import base


@ddt.ddt
class TestTestrConf(base.TestCase):

    @mock.patch.object(config_file.configparser, 'ConfigParser')
    def setUp(self, mock_ConfigParser):
        super().setUp()
        self._testr_conf = config_file.TestrConf(mock.sentinel.config_file)
        self._testr_conf.parser = mock.Mock()

    @mock.patch.object(config_file.util, 'get_repo_open')
    @mock.patch.object(config_file.test_processor, 'TestProcessorFixture')
    @mock.patch.object(config_file, 'sys')
    @mock.patch('os.path.exists', new=lambda x: True)
    def _check_get_run_command(self, mock_sys, mock_TestProcessorFixture,
                               mock_get_repo_open, platform='win32',
                               group_regex='.*', parallel_class=False,
                               sys_executable='/usr/bin/python',
                               expected_python='/usr/bin/python',
                               expected_group_callback=mock.ANY,
                               environment=None):
        mock_sys.platform = platform
        mock_sys.executable = sys_executable
        if environment is None:
            environment = {'PYTHON': ''}

        with mock.patch.dict('os.environ', environment):
            fixture = \
                self._testr_conf.get_run_command(test_path='fake_test_path',
                                                 top_dir='fake_top_dir',
                                                 group_regex=group_regex,
                                                 parallel_class=parallel_class)

        self.assertEqual(mock_TestProcessorFixture.return_value, fixture)
        mock_get_repo_open.assert_called_once_with(repo_url=None)
        command = '"%s" -m stestr.subunit_runner.run discover -t "%s" "%s" ' \
                  '$LISTOPT $IDOPTION' % (expected_python, 'fake_top_dir',
                                          'fake_test_path')
        # Ensure TestProcessorFixture is created with defaults except for where
        # we specfied and with the correct python.
        mock_TestProcessorFixture.assert_called_once_with(
            None, command, "--list", "--load-list $IDFILE",
            mock_get_repo_open.return_value,
            exclude_regex=None,
            exclude_list=None, concurrency=0,
            group_callback=expected_group_callback,
            test_filters=None, randomize=False, serial=False,
            include_list=None, worker_path=None)

    @mock.patch.object(config_file, 'sys')
    def _check_get_run_command_exception(self, mock_sys, platform='win32',
                                         sys_executable='/usr/bin/python',
                                         environment=None):
        mock_sys.platform = platform
        mock_sys.executable = sys_executable
        if environment is None:
            environment = {'PYTHON': ''}

        with mock.patch.dict('os.environ', environment):
            self.assertRaises(RuntimeError, self._testr_conf.get_run_command,
                              test_path='fake_test_path',
                              top_dir='fake_top_dir')

    def test_get_run_command_linux(self):
        self._check_get_run_command(
            platform='linux2',
            expected_python='/usr/bin/python')

    def test_get_run_command_emptysysexecutable_noenv(self):
        self._check_get_run_command_exception(
            platform='linux2',
            sys_executable=None)

    def test_get_run_command_emptysysexecutable_win32(self):
        self._check_get_run_command_exception(
            platform='win32', sys_executable=None,
            environment={'PYTHON': 'python3'})

    def test_get_run_command_emptysysexecutable_withenv(self):
        self._check_get_run_command(
            platform='linux2', sys_executable=None,
            expected_python='${PYTHON}',
            environment={'PYTHON': '/usr/bin/python3'})

    def test_get_run_command_win32(self):
        self._check_get_run_command()

    def test_get_run_command_parallel_class(self):
        self._check_get_run_command(parallel_class=True)

    def test_get_run_command_nogroup_regex_noparallel_class(self):
        self._testr_conf.parser.has_option.return_value = False
        self._check_get_run_command(group_regex='',
                                    expected_group_callback=None)

    @ddt.data(('.\\', '.\\\\'),
              ('a\\b\\', 'a\\b\\\\'),
              ('a\\b', 'a\\b'))
    @ddt.unpack
    @mock.patch('os.sep', new='\\')
    def test_sanitize_dir_win32(self, path, expected):
        sanitized = self._testr_conf._sanitize_path(path)
        self.assertEqual(expected, sanitized)
