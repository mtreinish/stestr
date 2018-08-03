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

import functools
import io
import os
import re
import shutil
import subprocess
import tempfile

import fixtures
import six
from six import StringIO
import subunit as subunit_lib
import testtools

from stestr.commands import list as list_cmd
from stestr.commands import run
from stestr.tests import base


class TestReturnCodes(base.TestCase):
    def setUp(self):
        super(TestReturnCodes, self).setUp()
        # Setup test dirs
        self.directory = tempfile.mkdtemp(prefix='stestr-unit')
        self.addCleanup(shutil.rmtree, self.directory, ignore_errors=True)
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

    def _check_subunit(self, output_stream):
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

    def test_parallel_passing(self):
        self.assertRunExit('stestr run passing', 0)

    def test_parallel_passing_bad_regex(self):
        self.assertRunExit('stestr run bad.regex.foobar', 1)

    def test_parallel_fails(self):
        self.assertRunExit('stestr run', 1)

    def test_parallel_passing_xfail(self):
        self.assertRunExit('stestr run xfail', 0)

    def test_parallel_fails_unxsuccess(self):
        self.assertRunExit('stestr run unexpected', 1)

    def test_parallel_blacklist(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        with os.fdopen(fd, 'w') as blacklist:
            blacklist.write('fail')
        cmd = 'stestr run --blacklist-file %s' % path
        self.assertRunExit(cmd, 0)

    def test_parallel_whitelist(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        with os.fdopen(fd, 'w') as whitelist:
            whitelist.write('passing')
        cmd = 'stestr run --whitelist-file %s' % path
        self.assertRunExit(cmd, 0)

    def test_serial_passing(self):
        self.assertRunExit('stestr run --serial passing', 0)

    def test_serial_fails(self):
        self.assertRunExit('stestr run --serial', 1)

    def test_serial_blacklist(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        with os.fdopen(fd, 'w') as blacklist:
            blacklist.write('fail')
        cmd = 'stestr run --serial --blacklist-file %s' % path
        self.assertRunExit(cmd, 0)

    def test_serial_whitelist(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        with os.fdopen(fd, 'w') as whitelist:
            whitelist.write('passing')
        cmd = 'stestr run --serial --whitelist-file %s' % path
        self.assertRunExit(cmd, 0)

    def test_serial_subunit_passing(self):
        self.assertRunExit('stestr run --subunit passing', 0,
                           subunit=True)

    def test_parallel_subunit_passing(self):
        self.assertRunExit('stestr run --subunit passing', 0,
                           subunit=True)

    def test_slowest_passing(self):
        self.assertRunExit('stestr run --slowest passing', 0)

    def test_slowest_failing(self):
        self.assertRunExit('stestr run --slowest failing', 1)

    def test_until_failure_fails(self):
        self.assertRunExit('stestr run --until-failure', 1)

    def test_until_failure_with_subunit_fails(self):
        self.assertRunExit('stestr run --until-failure --subunit', 1,
                           subunit=True)

    def test_list(self):
        self.assertRunExit('stestr list', 0)

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

    def test_load_from_stdin(self):
        self.assertRunExit('stestr run passing', 0)
        stream = self._get_cmd_stdout(
            'stestr last --subunit')[0]
        self.assertRunExit('stestr load', 0, stdin=stream)

    def test_load_from_stdin_quiet(self):
        out, err = self.assertRunExit('stestr -q run passing', 0)
        self.assertEqual(out.decode('utf-8'), '')
        # FIXME(masayukig): We get some warnings when we run a coverage job.
        # So, just ignore 'err' here.
        stream = self._get_cmd_stdout(
            'stestr last --subunit')[0]
        out, err = self.assertRunExit('stestr -q load', 0, stdin=stream)
        self.assertEqual(out.decode('utf-8'), '')
        self.assertEqual(err.decode('utf-8'), '')

    def test_no_subunit_trace_force_subunit_trace(self):
        out, err = self.assertRunExit(
            'stestr run --no-subunit-trace --force-subunit-trace passing', 0)
        out = six.text_type(out)
        self.assertNotIn('PASSED (id=0)', out)
        self.assertIn('Totals', out)
        self.assertIn('Worker Balance', out)
        self.assertIn('Sum of execute time for each test:', out)

    def test_parallel_passing_from_func(self):
        stdout = fixtures.StringStream('stdout')
        self.useFixture(stdout)
        self.assertEqual(0, run.run_command(filters=['passing'],
                                            stdout=stdout.stream))

    def test_parallel_passing_bad_regex_from_func(self):
        stdout = fixtures.StringStream('stdout')
        self.useFixture(stdout)
        self.assertEqual(1, run.run_command(filters=['bad.regex.foobar'],
                                            stdout=stdout.stream))

    def test_parallel_fails_from_func(self):
        stdout = fixtures.StringStream('stdout')
        self.useFixture(stdout)
        self.assertEqual(1, run.run_command(stdout=stdout.stream))

    def test_serial_passing_from_func(self):
        stdout = fixtures.StringStream('stdout')
        self.useFixture(stdout)
        self.assertEqual(0, run.run_command(filters=['passing'], serial=True,
                                            stdout=stdout.stream))

    def test_serial_fails_from_func(self):
        stdout = fixtures.StringStream('stdout')
        self.useFixture(stdout)
        self.assertEqual(1, run.run_command(serial=True, stdout=stdout.stream))

    def test_serial_subunit_passing_from_func(self):
        stdout = io.BytesIO()
        self.assertEqual(0, run.run_command(subunit_out=True, serial=True,
                                            filters=['passing'],
                                            stdout=stdout))
        stdout.seek(0)
        self._check_subunit(stdout)

    def test_parallel_subunit_passing_from_func(self):
        stdout = io.BytesIO()
        self.assertEqual(0, run.run_command(subunit_out=True,
                                            filters=['passing'],
                                            stdout=stdout))
        stdout.seek(0)
        self._check_subunit(stdout)

    def test_until_failure_fails_from_func(self):
        stdout = fixtures.StringStream('stdout')
        self.useFixture(stdout)
        self.assertEqual(1, run.run_command(until_failure=True,
                                            stdout=stdout.stream))

    def test_until_failure_with_subunit_fails_from_func(self):
        stdout = io.BytesIO()
        self.assertEqual(1, run.run_command(until_failure=True,
                                            subunit_out=True,
                                            stdout=stdout))
        stdout.seek(0)
        self._check_subunit(stdout)

    def test_list_from_func(self):
        stdout = fixtures.StringStream('stdout')
        self.useFixture(stdout)
        self.assertEqual(0, list_cmd.list_command(stdout=stdout.stream))
