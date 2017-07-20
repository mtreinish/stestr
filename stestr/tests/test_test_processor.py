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

import subprocess

import mock

from stestr import test_processor
from stestr.tests import base


class TestTestProcessorFixture(base.TestCase):

    def setUp(self):
        super(TestTestProcessorFixture, self).setUp()
        self._fixture = test_processor.TestProcessorFixture(
            mock.sentinel.test_ids, mock.sentinel.options,
            mock.sentinel.cmd_template, mock.sentinel.listopt,
            mock.sentinel.idoption, mock.sentinel.repository)

    @mock.patch.object(subprocess, 'Popen')
    @mock.patch.object(test_processor, 'sys')
    def _check_start_process(self, mock_sys, mock_Popen, platform='win32',
                             expected_fn=None):
        mock_sys.platform = platform

        self._fixture._start_process(mock.sentinel.cmd)

        mock_Popen.assert_called_once_with(
            mock.sentinel.cmd, shell=True, stdout=subprocess.PIPE,
            stdin=subprocess.PIPE, preexec_fn=expected_fn)

    def test_start_process_win32(self):
        self._check_start_process()

    def test_start_process_linux(self):
        self._check_start_process(
            platform='linux2', expected_fn=self._fixture._clear_SIGPIPE)
