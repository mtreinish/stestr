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
    @mock.patch.object(config_file.test_listing_fixture, 'TestListingFixture')
    @mock.patch.object(config_file, 'sys')
    def _check_get_run_command(self, mock_sys, mock_TestListingFixture,
                               mock_get_repo_open, platform='win32',
                               expected_python='python'):
        mock_sys.platform = platform
        mock_options = mock.Mock()
        mock_options.test_path = 'fake_test_path'
        mock_options.top_dir = 'fake_top_dir'
        mock_options.group_regex = '.*'

        fixture = self._testr_conf.get_run_command(mock_options,
                                                   mock.sentinel.test_ids,
                                                   mock.sentinel.regexes)

        self.assertEqual(mock_TestListingFixture.return_value, fixture)
        mock_get_repo_open.assert_called_once_with(mock_options.repo_type,
                                                   mock_options.repo_url)
        command = "%s -m subunit.run discover -t %s %s $LISTOPT $IDOPTION" % (
            expected_python, mock_options.top_dir, mock_options.test_path)
        mock_TestListingFixture.assert_called_once_with(
            mock.sentinel.test_ids, mock_options, command, "--list",
            "--load-list $IDFILE", mock_get_repo_open.return_value,
            test_filters=mock.sentinel.regexes, group_callback=mock.ANY)

    def test_get_run_command_linux(self):
        self._check_get_run_command(platform='linux2',
                                    expected_python='${PYTHON:-python}')

    def test_get_run_command_win32(self):
        self._check_get_run_command()
