# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import re
import shutil
import subprocess
import tempfile

import six
from six import StringIO

from stestr.tests import base

DEVNULL = open(os.devnull, 'wb')


class TestReturnCodes(base.TestCase):
    def setUp(self):
        super(TestReturnCodes, self).setUp()
        # Setup test dirs
        self.directory = tempfile.mkdtemp(prefix='stestr-unit')
        self.addCleanup(shutil.rmtree, self.directory)
        self.test_dir = os.path.join(self.directory, 'tests')
        os.mkdir(self.test_dir)
        # Setup Test files
        self.testr_conf_file = os.path.join(self.directory, '.stestr.conf')
        self.setup_cfg_file = os.path.join(self.directory, 'setup.cfg')
        self.passing_file = os.path.join(self.test_dir, 'test_passing.py')
        self.failing_file = os.path.join(self.test_dir, 'test_failing.py')
        self.init_file = os.path.join(self.test_dir, '__init__.py')
        self.setup_py = os.path.join(self.directory, 'setup.py')
        shutil.copy('stestr/tests/files/testr-conf', self.testr_conf_file)
        shutil.copy('stestr/tests/files/passing-tests', self.passing_file)
        shutil.copy('stestr/tests/files/failing-tests', self.failing_file)
        shutil.copy('setup.py', self.setup_py)
        shutil.copy('stestr/tests/files/setup.cfg', self.setup_cfg_file)
        shutil.copy('stestr/tests/files/__init__.py', self.init_file)

        self.stdout = StringIO()
        self.stderr = StringIO()
        # Change directory, run wrapper and check result
        self.addCleanup(os.chdir, os.path.abspath(os.curdir))
        os.chdir(self.directory)
        subprocess.call('stestr init', shell=True)

    def assertRunExit(self, cmd, expected, subunit=False):
        p = subprocess.Popen(
            "%s" % cmd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()

        if not subunit:
            self.assertEqual(
                p.returncode, expected,
                "Stdout: %s; Stderr: %s" % (out, err))
        else:
            self.assertEqual(p.returncode, expected,
                             "Expected return code: %s doesn't match actual "
                             "return code of: %s" % (expected, p.returncode))

    def test_parallel_passing(self):
        self.assertRunExit('stestr run passing', 0)

    def test_parallel_passing_bad_regex(self):
        self.assertRunExit('stestr run bad.regex.foobar', 1)

    def test_parallel_fails(self):
        self.assertRunExit('stestr run', 1)

    def test_serial_passing(self):
        self.assertRunExit('stestr run --serial passing', 0)

    def test_serial_fails(self):
        self.assertRunExit('stestr run --serial', 1)

    def test_serial_subunit_passing(self):
        self.assertRunExit('stestr run --subunit passing', 0,
                           subunit=True)

    def test_parallel_subunit_passing(self):
        self.assertRunExit('stestr run --subunit passing', 0,
                           subunit=True)

    def test_until_failure_fails(self):
        self.assertRunExit('stestr run --until-failure', 1)

    def test_until_failure_with_subunit_fails(self):
        self.assertRunExit('stestr run --until-failure --subunit', 1,
                           subunit=True)

    def test_list(self):
        self.assertRunExit('stestr list', 0)

    def test_no_command(self):
        self.assertRunExit('stestr', 2)

    def _get_cmd_stdout(self, cmd):
        p = subprocess.Popen(cmd, shell=True,
                             stdout=subprocess.PIPE)
        out = p.communicate()
        self.assertEqual(0, p.returncode)
        return out

    def test_combine_results(self):
        self.assertRunExit('stestr run passing', 0)
        stdout = self._get_cmd_stdout(
            'stestr last --no-subunit-trace')
        stdout = six.text_type(stdout[0])
        test_count_split = stdout.split(' ')
        test_count = test_count_split[1]
        test_count = int(test_count)
        id_regex = re.compile('\(id=(.*?)\)')
        test_id = id_regex.search(stdout).group(0)
        self.assertRunExit('stestr run --combine passing', 0)
        combine_stdout = self._get_cmd_stdout(
            'stestr last --no-subunit-trace')[0]
        combine_stdout = six.text_type(combine_stdout)
        combine_test_count_split = combine_stdout.split(' ')
        combine_test_count = combine_test_count_split[1]
        combine_test_count = int(combine_test_count)
        combine_test_id = id_regex.search(combine_stdout).group(0)
        self.assertEqual(test_id, combine_test_id)

        # The test results from running the same tests twice with combine
        # should return a test count 2x as big at the end of the run
        self.assertEqual(test_count * 2, combine_test_count)
