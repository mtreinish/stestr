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
import subunit as subunit_lib
import testtools

from stestr.commands import list as list_cmd
from stestr.commands import run
from stestr.tests import base


class TestReturnCodes(base.TestCase):
    def setUp(self):
        super().setUp()
        # Setup test dirs
        self.directory = tempfile.mkdtemp(prefix='stestr-unit')
        self.addCleanup(shutil.rmtree, self.directory, ignore_errors=True)
        self.test_dir = os.path.join(self.directory, 'tests')
        os.mkdir(self.test_dir)
        # Setup Test files
        self.repo_root = os.path.abspath(os.curdir)
        self.testr_conf_file = os.path.join(self.directory, '.stestr.conf')
        self.setup_cfg_file = os.path.join(self.directory, 'setup.cfg')
        self.passing_file = os.path.join(self.test_dir, 'test_passing.py')
        self.failing_file = os.path.join(self.test_dir, 'test_failing.py')
        self.init_file = os.path.join(self.test_dir, '__init__.py')
        self.setup_py = os.path.join(self.directory, 'setup.py')
        self.user_config = os.path.join(self.directory, 'stestr.yaml')
        shutil.copy('stestr/tests/files/testr-conf', self.testr_conf_file)
        shutil.copy('stestr/tests/files/passing-tests', self.passing_file)
        shutil.copy('stestr/tests/files/failing-tests', self.failing_file)
        shutil.copy('setup.py', self.setup_py)
        shutil.copy('stestr/tests/files/setup.cfg', self.setup_cfg_file)
        shutil.copy('stestr/tests/files/__init__.py', self.init_file)
        shutil.copy('stestr/tests/files/stestr.yaml', self.user_config)

        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        # Change directory, run wrapper and check result
        self.addCleanup(os.chdir, self.repo_root)
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
                "Stdout: {}; Stderr: {}".format(out, err))
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

    def test_parallel_exclusion_list(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        with os.fdopen(fd, 'w') as exclusion_list:
            exclusion_list.write('fail')
        cmd = 'stestr run --exclude-list %s' % path
        self.assertRunExit(cmd, 0)

    def test_parallel_whitelist(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        with os.fdopen(fd, 'w') as whitelist:
            whitelist.write('passing')
        cmd = 'stestr run --whitelist-file %s' % path
        self.assertRunExit(cmd, 0)

    def test_parallel_inclusion_list(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        with os.fdopen(fd, 'w') as inclusion_list:
            inclusion_list.write('passing')
        cmd = 'stestr run --include-list %s' % path
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

    def test_serial_exclusion_list(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        with os.fdopen(fd, 'w') as exclusion_list:
            exclusion_list.write('fail')
        cmd = 'stestr run --serial --exclude-list %s' % path
        self.assertRunExit(cmd, 0)

    def test_serial_whitelist(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        with os.fdopen(fd, 'w') as whitelist:
            whitelist.write('passing')
        cmd = 'stestr run --serial --whitelist-file %s' % path
        self.assertRunExit(cmd, 0)

    def test_serial_inclusion_list(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.remove, path)
        with os.fdopen(fd, 'w') as inclusion_list:
            inclusion_list.write('passing')
        cmd = 'stestr run --serial --include-list %s' % path
        self.assertRunExit(cmd, 0)

    def test_serial_subunit_passing(self):
        self.assertRunExit('stestr --user-config stestr.yaml run --subunit '
                           '--serial passing', 0, subunit=True)

    def test_serial_subunit_failing(self):
        self.assertRunExit('stestr --user-config stestr.yaml run --subunit '
                           '--serial failing', 0, subunit=True)

    def test_parallel_subunit_passing(self):
        self.assertRunExit('stestr --user-config stestr.yaml run --subunit '
                           'passing', 0, subunit=True)

    def test_parallel_subunit_failing(self):
        self.assertRunExit('stestr --user-config stestr.yaml run --subunit '
                           'failing', 0, subunit=True)

    def test_slowest_passing(self):
        self.assertRunExit('stestr run --slowest passing', 0)

    def test_slowest_failing(self):
        self.assertRunExit('stestr run --slowest failing', 1)

    def test_until_failure_fails(self):
        self.assertRunExit('stestr run --until-failure', 1)

    def test_until_failure_with_subunit_fails(self):
        self.assertRunExit('stestr --user-config stestr.yaml run '
                           '--until-failure --subunit', 1, subunit=True)

    def test_with_parallel_class(self):
        # NOTE(masayukig): Ideally, it's better to figure out the
        # difference between with --parallel-class and without
        # --parallel-class. However, it's difficult to make such a
        # test from a command line based test.
        self.assertRunExit('stestr --parallel-class run passing', 0)

    def test_no_repo_dir(self):
        stestr_repo_dir = os.path.join(self.directory, '.stestr')
        shutil.rmtree(stestr_repo_dir, ignore_errors=True)
        # We can use stestr run even if there's no repo directory.
        self.assertRunExit('stestr run passing', 0)

    def test_empty_repo_dir(self):
        stestr_repo_dir = os.path.join(self.directory, '.stestr')
        shutil.rmtree(stestr_repo_dir, ignore_errors=True)
        os.mkdir(stestr_repo_dir)
        # We can initialize an empty repo directory.
        self.assertRunExit('stestr run passing', 0)

    def test_non_empty_repo_dir(self):
        stestr_repo_dir = os.path.join(self.directory, '.stestr')
        shutil.rmtree(stestr_repo_dir, ignore_errors=True)
        os.mkdir(stestr_repo_dir)
        with open(os.path.join(stestr_repo_dir, 'foo'), 'wt') as stream:
            stream.write('1\n')
        # We can't initialize a non-empty repo directory.
        self.assertRunExit('stestr run passing', 1)

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
        stdout = str(stdout[0])
        test_count_split = stdout.split(' ')
        test_count = test_count_split[1]
        test_count = int(test_count)
        id_regex = re.compile(r'\(id=(.*?)\)')
        test_id = id_regex.search(stdout).group(0)
        self.assertRunExit('stestr run --combine passing', 0)
        combine_stdout = self._get_cmd_stdout(
            'stestr last --no-subunit-trace')[0]
        combine_stdout = str(combine_stdout)
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

    def test_load_force_init(self):
        self.assertRunExit('stestr run passing', 0)
        stream = self._get_cmd_stdout(
            'stestr last --subunit')[0]
        # NOTE: --force-init should work here because there is an properly
        # initialized repository.
        self.assertRunExit('stestr load --force-init', 0, stdin=stream)

    def test_load_force_init_invalid(self):
        self.assertRunExit('stestr run passing', 0)
        stream = self._get_cmd_stdout(
            'stestr last --subunit')[0]
        os.remove(os.path.join(self.directory, '.stestr', 'format'))
        # NOTE: --force-init should fail here because there is an invalid
        # repository.
        self.assertRunExit('stestr load --force-init', 1, stdin=stream)

    def test_load_from_stdin_quiet(self):
        out, err = self.assertRunExit('stestr --user-config stestr.yaml -q '
                                      'run passing', 0)
        self.assertEqual('', out.decode('utf-8'))
        # FIXME(masayukig): We get some warnings when we run a coverage job.
        # So, just ignore 'err' here.
        stream = self._get_cmd_stdout('stestr last --subunit')[0]
        out, err = self.assertRunExit('stestr --user-config stestr.yaml -q '
                                      'load', 0, stdin=stream)
        self.assertEqual(out.decode('utf-8'), '')
        self.assertEqual(err.decode('utf-8'), '')

    def test_history_list(self):
        self.assertRunExit('stestr run passing', 0)
        self.assertRunExit('stestr run', 1)
        self.assertRunExit('stestr run passing', 0)
        table = self.assertRunExit(
            'stestr history list', 0)[0].decode('utf8')
        self.assertIn("| 0      | True   |", table.split('\n')[3].rstrip())
        self.assertIn("| 1      | False  |", table.split('\n')[4].rstrip())
        self.assertIn("| 2      | True   |", table.split('\n')[5].rstrip())
        expected = """
+--------+--------+-----------+----------------------------------+
| Run ID | Passed | Runtime   | Date                             |
+--------+--------+-----------+----------------------------------+
""".rstrip()
        self.assertEqual(expected.strip(), '\n'.join(
            [x.rstrip() for x in table.split('\n')[:3]]).strip())

    def test_history_empty(self):
        table = self.assertRunExit(
            'stestr history list', 0)[0].decode('utf8')
        self.assertEqual("",
                         '\n'.join(
                             [x.rstrip() for x in table.split('\n')]).strip())

    def test_history_show_passing(self):
        self.assertRunExit('stestr run passing', 0)
        self.assertRunExit('stestr run', 1)
        self.assertRunExit('stestr run passing', 0)
        output, _ = self.assertRunExit('stestr history show 0', 0)
        lines = [x.rstrip() for x in output.decode('utf8').split('\n')]
        self.assertIn(' - Passed: 2', lines)
        self.assertIn(' - Failed: 0', lines)
        self.assertIn(' - Expected Fail: 1', lines)

    def test_history_show_failing(self):
        self.assertRunExit('stestr run passing', 0)
        self.assertRunExit('stestr run', 1)
        self.assertRunExit('stestr run passing', 0)
        output, _ = self.assertRunExit('stestr history show 1', 1)
        lines = [x.rstrip() for x in output.decode('utf8').split('\n')]
        self.assertIn(' - Passed: 2', lines)
        self.assertIn(' - Failed: 2', lines)
        self.assertIn(' - Expected Fail: 1', lines)
        self.assertIn(' - Unexpected Success: 1', lines)

    def test_history_show_invalid_id(self):
        self.assertRunExit('stestr run passing', 0)
        self.assertRunExit('stestr run', 1)
        self.assertRunExit('stestr run passing', 0)
        output, _ = self.assertRunExit('stestr history show 42', 1)
        self.assertEqual(output.decode('utf8').rstrip(), "'No such run.'")

    def test_history_remove(self):
        self.assertRunExit('stestr run passing', 0)
        self.assertRunExit('stestr run', 1)
        self.assertRunExit('stestr run passing', 0)
        self.assertRunExit('stestr history remove 1', 0)
        table = self.assertRunExit(
            'stestr history list', 0)[0].decode('utf8')
        self.assertIn("| 0      | True   |", table.split('\n')[3].rstrip())
        self.assertNotIn("| 1      | False  |", table.split('\n')[4].strip())
        self.assertIn("| 2      | True   |", table.split('\n')[4].rstrip())
        expected = """
+--------+--------+-----------+----------------------------------+
| Run ID | Passed | Runtime   | Date                             |
+--------+--------+-----------+----------------------------------+
""".strip()
        self.assertEqual(expected, '\n'.join(
            [x.rstrip() for x in table.split('\n')[:3]]))

    def test_no_subunit_trace_force_subunit_trace(self):
        out, err = self.assertRunExit(
            'stestr run --no-subunit-trace --force-subunit-trace passing', 0)
        out = str(out)
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

    def test_str_concurrency_passing_from_func(self):
        stdout = fixtures.StringStream('stdout')
        self.useFixture(stdout)
        self.assertEqual(0, run.run_command(filters=['passing'],
                                            concurrency='1',
                                            stdout=stdout.stream))

    def test_str_concurrency_fails_from_func(self):
        stdout = fixtures.StringStream('stdout')
        self.useFixture(stdout)
        self.assertEqual(1, run.run_command(concurrency='1',
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

    def test_run_no_discover_pytest_path(self):
        passing_string = 'tests/test_passing.py::FakeTestClass::test_pass_list'
        out, err = self.assertRunExit('stestr run -n %s' % passing_string, 0)
        lines = out.decode('utf8').splitlines()
        self.assertIn(' - Passed: 1', lines)
        self.assertIn(' - Failed: 0', lines)

    def test_run_no_discover_pytest_path_failing(self):
        passing_string = 'tests/test_failing.py::FakeTestClass::test_pass_list'
        out, err = self.assertRunExit('stestr run -n %s' % passing_string, 1)
        lines = out.decode('utf8').splitlines()
        self.assertIn(' - Passed: 0', lines)
        self.assertIn(' - Failed: 1', lines)

    def test_run_no_discover_file_path(self):
        passing_string = 'tests/test_passing.py'
        out, err = self.assertRunExit('stestr run -n %s' % passing_string, 0)
        lines = out.decode('utf8').splitlines()
        self.assertIn(' - Passed: 2', lines)
        self.assertIn(' - Failed: 0', lines)
        self.assertIn(' - Expected Fail: 1', lines)

    def test_run_no_discover_file_path_failing(self):
        passing_string = 'tests/test_failing.py'
        out, err = self.assertRunExit('stestr run -n %s' % passing_string, 1)
        lines = out.decode('utf8').splitlines()
        self.assertIn(' - Passed: 0', lines)
        self.assertIn(' - Failed: 2', lines)
        self.assertIn(' - Unexpected Success: 1', lines)


class TestReturnCodesToxIni(TestReturnCodes):
    def setUp(self):
        super().setUp()
        self.tox_ini_dir = os.path.join(self.directory, 'tox.ini')
        tox_file = os.path.join(self.repo_root, 'stestr/tests/files/tox.ini')
        shutil.copy(tox_file, self.tox_ini_dir)
        os.remove(self.testr_conf_file)
