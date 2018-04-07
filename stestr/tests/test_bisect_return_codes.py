# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import shutil
import subprocess
import tempfile

import six

from stestr.tests import base


class TestBisectReturnCodes(base.TestCase):
    def setUp(self):
        super(TestBisectReturnCodes, self).setUp()
        # Setup test dirs
        self.directory = tempfile.mkdtemp(prefix='stestr-unit')
        self.addCleanup(shutil.rmtree, self.directory)
        self.test_dir = os.path.join(self.directory, 'tests')
        os.mkdir(self.test_dir)
        # Setup Test files
        self.testr_conf_file = os.path.join(self.directory, '.stestr.conf')
        self.setup_cfg_file = os.path.join(self.directory, 'setup.cfg')
        self.init_file = os.path.join(self.test_dir, '__init__.py')
        self.setup_py = os.path.join(self.directory, 'setup.py')
        shutil.copy('stestr/tests/files/testr-conf', self.testr_conf_file)
        shutil.copy('setup.py', self.setup_py)
        shutil.copy('stestr/tests/files/setup.cfg', self.setup_cfg_file)
        shutil.copy('stestr/tests/files/__init__.py', self.init_file)

        # Move around the test code
        self.serial_fail_file = os.path.join(self.test_dir,
                                             'test_serial_fails.py')
        shutil.copy('stestr/tests/files/bisect-fail-serial-tests',
                    self.serial_fail_file)

        # Change directory, run wrapper and check result
        self.addCleanup(os.chdir, os.path.abspath(os.curdir))
        os.chdir(self.directory)
        subprocess.call('stestr init', shell=True)

    def test_bisect_serial_fail_detected(self):
        p = subprocess.Popen(
            "stestr run --serial", shell=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        out, err = p.communicate()
        self.assertEqual(1, p.returncode,
                         'stestr run returned an unexpected return code'
                         'Stdout: %s\nStderr: %s' % (out, err))
        p_analyze = subprocess.Popen(
            "stestr run --analyze-isolation", shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p_analyze.communicate()
        out = out.decode('utf-8')
        # For debugging potential failures
        lines = six.text_type(out.rstrip()).splitlines()
        self.assertEqual(3, p_analyze.returncode,
                         'Analyze isolation returned an unexpected return code'
                         'Stdout: %s\nStderr: %s' % (out, err))
        last_line = ('tests.test_serial_fails.TestFakeClass.test_B  '
                     'tests.test_serial_fails.TestFakeClass.test_A')
        self.assertEqual(last_line, lines[-1])
