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

import functools
import io
import os
import shutil
import subprocess
import tempfile

import six
from six import StringIO
import subunit as subunit_lib
import testtools
import yaml

from stestr.tests import base


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

    def _get_cmd_stdout(self, cmd):
        p = subprocess.Popen(cmd, shell=True,
                             stdout=subprocess.PIPE)
        out = p.communicate()
        self.assertEqual(0, p.returncode)
        return out

    def assertRunExit(self, cmd, expected, subunit=False, stdin=None):
        if stdin:
            p = subprocess.Popen(
                "%s" % cmd, shell=True, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate(stdin)
        else:
            p = subprocess.Popen(
                "%s" % cmd, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()

        if not subunit:
            self.assertEqual(
                p.returncode, expected,
                "Stdout: %s; Stderr: %s" % (out, err))
            return (out, err)
        else:
            self.assertEqual(p.returncode, expected,
                             "Expected return code: %s doesn't match actual "
                             "return code of: %s" % (expected, p.returncode))
            output_stream = io.BytesIO(out)
            stream = subunit_lib.ByteStreamToStreamResult(output_stream)
            starts = testtools.StreamResult()
            summary = testtools.StreamSummary()
            tests = []

            def _add_dict(test):
                tests.append(test)

            outcomes = testtools.StreamToDict(functools.partial(_add_dict))
            result = testtools.CopyStreamResult([starts, outcomes, summary])
            result.startTestRun()
            try:
                stream.run(result)
            finally:
                result.stopTestRun()
            self.assertThat(len(tests), testtools.matchers.GreaterThan(0))
            return (out, err)

    def test_empty_config_file_failing(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        conf_file = os.fdopen(fd, 'wb', 0)
        self.addCleanup(conf_file.close)
        self.assertRunExit(
            'stestr --user-config=%s run' % path, 1)

    def test_empty_config_file_passing(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        conf_file = os.fdopen(fd, 'wb', 0)
        self.addCleanup(conf_file.close)
        self.assertRunExit(
            'stestr --user-config=%s run passing' % path, 0)

    def test_no_subunit_trace_config_file_passing(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        conf_file = os.fdopen(fd, 'wb', 0)
        self.addCleanup(conf_file.close)
        contents = six.text_type(
            yaml.dump({
                'run': {
                    'no-subunit-trace': True,
                }
            }, default_flow_style=False))
        conf_file.write(contents.encode('utf-8'))
        out, err = self.assertRunExit(
            'stestr --user-config=%s run passing' % path, 0)
        out = six.text_type(out)
        self.assertIn('PASSED (id=0)', out)
        self.assertNotIn('Totals', out)
        self.assertNotIn('Worker Balance', out)
        self.assertNotIn('Sum of execute time for each test:', out)
        self.assertNotIn('Runtime (s)', out)

    def test_no_subunit_trace_config_file_failing(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        conf_file = os.fdopen(fd, 'wb', 0)
        self.addCleanup(conf_file.close)
        contents = six.text_type(
            yaml.dump({
                'run': {
                    'no-subunit-trace': True,
                }
            }, default_flow_style=False))
        conf_file.write(contents.encode('utf-8'))
        out, err = self.assertRunExit(
            'stestr --user-config=%s run' % path, 1)
        out = six.text_type(out)
        self.assertIn('FAILED (id=0, failures=2)', out)
        self.assertNotIn('Totals', out)
        self.assertNotIn('Worker Balance', out)
        self.assertNotIn('Sum of execute time for each test:', out)

    def test_no_subunit_trace_config_file_force_subunit_trace(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        conf_file = os.fdopen(fd, 'wb', 0)
        self.addCleanup(conf_file.close)
        contents = six.text_type(
            yaml.dump({
                'run': {
                    'no-subunit-trace': True,
                }
            }, default_flow_style=False))
        conf_file.write(contents.encode('utf-8'))
        out, err = self.assertRunExit(
            'stestr --user-config=%s run --force-subunit-trace passing' % path,
            0)
        out = six.text_type(out)
        self.assertNotIn('PASSED (id=0)', out)
        self.assertIn('Totals', out)
        self.assertIn('Worker Balance', out)
        self.assertIn('Sum of execute time for each test:', out)

    def test_abbreviate_config_file_passing(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        conf_file = os.fdopen(fd, 'wb', 0)
        self.addCleanup(conf_file.close)
        contents = six.text_type(
            yaml.dump({
                'run': {
                    'abbreviate': True,
                }
            }, default_flow_style=False))
        conf_file.write(contents.encode('utf-8'))
        out, err = self.assertRunExit(
            'stestr --user-config=%s run passing' % path, 0)
        out = six.text_type(out)
        self.assertIn('..', out)
        self.assertNotIn('PASSED (id=0)', out)
        self.assertIn('Totals', out)
        self.assertIn('Worker Balance', out)
        self.assertIn('Sum of execute time for each test:', out)

    def test_abbreviate_config_file_failing(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        conf_file = os.fdopen(fd, 'wb', 0)
        self.addCleanup(conf_file.close)
        contents = six.text_type(
            yaml.dump({
                'run': {
                    'abbreviate': True,
                }
            }, default_flow_style=False))
        conf_file.write(contents.encode('utf-8'))
        # NOTE(mtreinish): Running serially here to ensure a consistent
        # execution order for confirming the abbreviated output.
        out, err = self.assertRunExit(
            'stestr --user-config=%s run --serial' % path, 1)
        out = six.text_type(out)
        self.assertIn('FF..', out)
        self.assertNotIn('FAILED (id=0, failures=2)', out)
        self.assertIn('Totals', out)
        self.assertIn('Worker Balance', out)
        self.assertIn('Sum of execute time for each test:', out)

    def test_no_subunit_trace_slowest_config_file_passing(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        conf_file = os.fdopen(fd, 'wb', 0)
        self.addCleanup(conf_file.close)
        contents = six.text_type(
            yaml.dump({
                'run': {
                    'no-subunit-trace': True,
                    'slowest': True,
                }
            }, default_flow_style=False))
        conf_file.write(contents.encode('utf-8'))
        out, err = self.assertRunExit(
            'stestr --user-config=%s run passing' % path, 0)
        out = six.text_type(out)
        self.assertIn('PASSED (id=0)', out)
        self.assertNotIn('Totals', out)
        self.assertNotIn('Worker Balance', out)
        self.assertNotIn('Sum of execute time for each test:', out)
        self.assertIn('Runtime (s)', out)

    def test_failing_list_config_file(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        conf_file = os.fdopen(fd, 'wb', 0)
        self.addCleanup(conf_file.close)
        contents = six.text_type(
            yaml.dump({
                'run': {
                    'no-subunit-trace': True,
                    'slowest': True,
                },
                'failing': {
                    'list': True
                }
            }, default_flow_style=False))
        conf_file.write(contents.encode('utf-8'))
        self.assertRunExit('stestr --user-config=%s run' % path, 1)
        out, err = self.assertRunExit('stestr --user-config=%s failing' % path,
                                      1)
        out = six.text_type(out)
        self.assertNotIn('FAILED (id=0, failures=2)', out)
        self.assertNotIn('FAIL:', out)
        self.assertIn('tests.test_failing.FakeTestClass.test_pass', out)
        self.assertIn('tests.test_failing.FakeTestClass.test_pass_list', out)

    def test_no_subunit_trace_last_config_file_passing(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        conf_file = os.fdopen(fd, 'wb', 0)
        self.addCleanup(conf_file.close)
        contents = six.text_type(
            yaml.dump({
                'run': {
                    'slowest': True,
                },
                'failing': {
                    'list': True
                },
                'last': {
                    'no-subunit-trace': True,
                },
            }, default_flow_style=False))
        conf_file.write(contents.encode('utf-8'))
        run_out, run_err = self.assertRunExit(
            'stestr --user-config=%s run passing' % path, 0)
        out, err = self.assertRunExit('stestr --user-config=%s last' % path,
                                      0)
        run_out = six.text_type(run_out)
        out = six.text_type(out)
        self.assertIn('PASSED (id=0)', out)
        self.assertNotIn('Totals', out)
        self.assertNotIn('Worker Balance', out)
        self.assertNotIn('Sum of execute time for each test:', out)
        self.assertNotIn('Runtime (s)', out)
        self.assertIn('Totals', run_out)
        self.assertIn('Worker Balance', run_out)
        self.assertIn('Sum of execute time for each test:', run_out)
        self.assertIn('Runtime (s)', run_out)

    def test_subunit_trace_load_from_config_passing(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        conf_file = os.fdopen(fd, 'wb', 0)
        self.addCleanup(conf_file.close)
        contents = six.text_type(
            yaml.dump({
                'run': {
                    'slowest': True,
                },
                'failing': {
                    'list': True
                },
                'last': {
                    'no-subunit-trace': True,
                },
                'load': {
                    'subunit-trace': True,
                }
            }, default_flow_style=False))
        conf_file.write(contents.encode('utf-8'))

        self.assertRunExit('stestr --user-config=%s run passing' % path, 0)
        stream = self._get_cmd_stdout(
            'stestr --user-config=%s last --subunit' % path)[0]
        out, err = self.assertRunExit('stestr --user-config=%s load' % path,
                                      0, stdin=stream)
        out = six.text_type(out)
        self.assertNotIn('PASSED (id=0)', out)
        self.assertIn('Totals', out)
        self.assertIn('Worker Balance', out)
        self.assertIn('Sum of execute time for each test:', out)

    def test_subunit_trace_load_from_config_failing(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        conf_file = os.fdopen(fd, 'wb', 0)
        self.addCleanup(conf_file.close)
        contents = six.text_type(
            yaml.dump({
                'run': {
                    'slowest': True,
                },
                'failing': {
                    'list': True
                },
                'last': {
                    'no-subunit-trace': True,
                },
                'load': {
                    'subunit-trace': True,
                }
            }, default_flow_style=False))
        conf_file.write(contents.encode('utf-8'))

        self.assertRunExit('stestr --user-config=%s run' % path, 1)
        stream = self._get_cmd_stdout(
            'stestr --user-config=%s last --subunit' % path)[0]
        out, err = self.assertRunExit('stestr --user-config=%s load' % path,
                                      0, stdin=stream)
        out = six.text_type(out)
        self.assertNotIn('FAILED (id=0, failures=2)', out)
        self.assertNotIn('FF..', out)
        self.assertIn('Totals', out)
        self.assertIn('Worker Balance', out)
        self.assertIn('Sum of execute time for each test:', out)

    @testtools.skip('Abbreviated output not displaying')
    def test_abbreviate_load_from_config_passing(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        conf_file = os.fdopen(fd, 'wb', 0)
        self.addCleanup(conf_file.close)
        contents = six.text_type(
            yaml.dump({
                'run': {
                    'slowest': True,
                },
                'failing': {
                    'list': True
                },
                'last': {
                    'no-subunit-trace': True,
                },
                'load': {
                    'abbreviate': True,
                }
            }, default_flow_style=False))
        conf_file.write(contents.encode('utf-8'))

        self.assertRunExit('stestr --user-config=%s run passing' % path, 0)
        stream = self._get_cmd_stdout(
            'stestr --user-config=%s last --subunit' % path)[0]
        out, err = self.assertRunExit('stestr --user-config=%s load' % path,
                                      0, stdin=stream)
        out = six.text_type(out)
        self.assertNotIn('PASSED (id=0)', out)
        self.assertIn('..', out)
        self.assertIn('Totals', out)
        self.assertIn('Worker Balance', out)
        self.assertIn('Sum of execute time for each test:', out)

    @testtools.skip('Abbreviated output not displaying')
    def test_abbreviate_load_from_config_failing(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        conf_file = os.fdopen(fd, 'wb', 0)
        self.addCleanup(conf_file.close)
        contents = six.text_type(
            yaml.dump({
                'run': {
                    'slowest': True,
                },
                'failing': {
                    'list': True
                },
                'last': {
                    'no-subunit-trace': True,
                },
                'load': {
                    'abbreviate': True,
                }
            }, default_flow_style=False))
        conf_file.write(contents.encode('utf-8'))
        # NOTE(mtreinish): Running serially here to ensure a consistent
        # execution order for confirming the abbreviated output.
        self.assertRunExit('stestr --user-config=%s run --serial' % path, 1)
        stream = self._get_cmd_stdout(
            'stestr --user-config=%s last --subunit' % path)[0]
        out, err = self.assertRunExit('stestr --user-config=%s load' % path,
                                      0, stdin=stream)
        out = six.text_type(out)
        self.assertNotIn('FAILED (id=0, failures=2)', out)
        self.assertIn('FF..', out)
        self.assertIn('Totals', out)
        self.assertIn('Worker Balance', out)
        self.assertIn('Sum of execute time for each test:', out)
