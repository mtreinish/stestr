#
# Copyright (c) 2010 Testrepository Contributors
# 
# Licensed under either the Apache License, Version 2.0 or the BSD 3-clause
# license at the users choice. A copy of both licenses are available in the
# project source as Apache-2.0 and BSD. You may not use this file except in
# compliance with one of these two licences.
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under these licenses is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# license you chose for the specific language governing permissions and
# limitations under that license.

"""Tests for the run command."""

from io import BytesIO
import os.path
from subprocess import PIPE
import tempfile

from extras import try_import
from fixtures import (
    Fixture,
    MonkeyPatch,
    )
import subunit
v2_avail = try_import('subunit.ByteStreamToStreamResult')
from subunit import RemotedTestCase
from testscenarios.scenarios import multiply_scenarios
from testtools.compat import _b
from testtools.matchers import (
    Equals,
    MatchesException,
    MatchesListwise,
    )

from testrepository.commands import run
from testrepository.ui.model import UI, ProcessModel
from testrepository.repository import memory
from testrepository.testlist import write_list
from testrepository.tests import ResourcedTestCase, Wildcard
from testrepository.tests.stubpackage import TempDirResource
from testrepository.tests.test_testcommand import FakeTestCommand
from testrepository.tests.test_repository import make_test


class TestCommand(ResourcedTestCase):

    resources = [('tempdir', TempDirResource())]

    def get_test_ui_and_cmd(self, options=(), args=(), proc_outputs=(),
        proc_results=()):
        self.dirty()
        ui = UI(options=options, args=args, proc_outputs=proc_outputs,
            proc_results=proc_results)
        ui.here = self.tempdir
        cmd = run.run(ui)
        ui.set_command(cmd)
        return ui, cmd

    def dirty(self):
        # Ugly: TODO - improve testresources to make this go away.
        dict(self.resources)['tempdir']._dirty = True

    def config_path(self):
        return os.path.join(self.tempdir, '.testr.conf')

    def set_config(self, text):
        with open(self.config_path(), 'wt') as stream:
            stream.write(text)

    def setup_repo(self, cmd, ui, failures=True):
        repo = cmd.repository_factory.initialise(ui.here)
        inserter = repo.get_inserter()
        inserter.startTestRun()
        make_test('passing', True).run(inserter)
        if failures:
            make_test('failing1', False).run(inserter)
            make_test('failing2', False).run(inserter)
        inserter.stopTestRun()

    def test_no_config_file_errors(self):
        ui, cmd = self.get_test_ui_and_cmd()
        cmd.repository_factory.initialise(ui.here)
        self.assertEqual(3, cmd.execute())
        self.assertEqual(1, len(ui.outputs))
        self.assertEqual('error', ui.outputs[0][0])
        self.assertThat(ui.outputs[0][1],
            MatchesException(ValueError('No .testr.conf config file')))

    def test_no_config_settings_errors(self):
        ui, cmd = self.get_test_ui_and_cmd()
        cmd.repository_factory.initialise(ui.here)
        self.set_config('')
        self.assertEqual(3, cmd.execute())
        self.assertEqual(1, len(ui.outputs))
        self.assertEqual('error', ui.outputs[0][0])
        self.assertThat(ui.outputs[0][1], MatchesException(ValueError(
            'No test_command option present in .testr.conf')))

    def test_IDFILE_failures(self):
        ui, cmd = self.get_test_ui_and_cmd(options=[('failing', True)])
        cmd.repository_factory = memory.RepositoryFactory()
        self.setup_repo(cmd, ui)
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDOPTION\ntest_id_option=--load-list $IDFILE\n')
        cmd.command_factory = FakeTestCommand
        result = cmd.execute()
        listfile = os.path.join(ui.here, 'failing.list')
        expected_cmd = 'foo --load-list %s' % listfile
        self.assertEqual([
            ('values', [('running', expected_cmd)]),
            ('popen', (expected_cmd,),
             {'shell': True, 'stdin': PIPE, 'stdout': PIPE}),
            ('results', Wildcard),
            ('summary', True, 0, -3, None, None, [('id', 1, None)])
            ], ui.outputs)
        # TODO: check the list file is written, and deleted.
        self.assertEqual(0, result)

    def test_IDLIST_failures(self):
        ui, cmd = self.get_test_ui_and_cmd(options=[('failing', True)])
        cmd.repository_factory = memory.RepositoryFactory()
        self.setup_repo(cmd, ui)
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDLIST\n')
        self.assertEqual(0, cmd.execute())
        expected_cmd = 'foo failing1 failing2'
        self.assertEqual([
            ('values', [('running', expected_cmd)]),
            ('popen', (expected_cmd,),
             {'shell': True, 'stdin': PIPE, 'stdout': PIPE}),
            ('results', Wildcard),
            ('summary', True, 0, -3, None, None, [('id', 1, None)]),
            ], ui.outputs)
        # Failing causes partial runs to be used.
        self.assertEqual(True,
            cmd.repository_factory.repos[ui.here].get_test_run(1)._partial)

    def test_IDLIST_default_is_empty(self):
        ui, cmd = self.get_test_ui_and_cmd()
        cmd.repository_factory = memory.RepositoryFactory()
        self.setup_repo(cmd, ui)
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDLIST\n')
        self.assertEqual(0, cmd.execute())
        expected_cmd = 'foo '
        self.assertEqual([
            ('values', [('running', expected_cmd)]),
            ('popen', (expected_cmd,),
             {'shell': True, 'stdin': PIPE, 'stdout': PIPE}),
            ('results', Wildcard),
            ('summary', True, 0, -3, None, None, [('id', 1, None)])
            ], ui.outputs)

    def test_IDLIST_default_passed_normally(self):
        ui, cmd = self.get_test_ui_and_cmd()
        cmd.repository_factory = memory.RepositoryFactory()
        self.setup_repo(cmd, ui)
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDLIST\ntest_id_list_default=whoo yea\n')
        self.assertEqual(0, cmd.execute())
        expected_cmd = 'foo whoo yea'
        self.assertEqual([
            ('values', [('running', expected_cmd)]),
            ('popen', (expected_cmd,),
             {'shell': True, 'stdin': PIPE, 'stdout': PIPE}),
            ('results', Wildcard),
            ('summary', True, 0, -3, None, None, [('id', 1, None)])
            ], ui.outputs)

    def test_IDFILE_not_passed_normally(self):
        ui, cmd = self.get_test_ui_and_cmd()
        cmd.repository_factory = memory.RepositoryFactory()
        self.setup_repo(cmd, ui)
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDOPTION\ntest_id_option=--load-list $IDFILE\n')
        self.assertEqual(0, cmd.execute())
        expected_cmd = 'foo '
        self.assertEqual([
            ('values', [('running', expected_cmd)]),
            ('popen', (expected_cmd,),
             {'shell': True, 'stdin': PIPE, 'stdout': PIPE}),
            ('results', Wildcard),
            ('summary', True, 0, -3, None, None, [('id', 1, None)]),
            ], ui.outputs)

    def capture_ids(self):
        params = []
        def capture_ids(self, ids, args, test_filters=None):
            params.append(self)
            params.append(ids)
            params.append(args)
            params.append(test_filters)
            result = Fixture()
            result.run_tests = lambda:[]
            return result
        return params, capture_ids

    def test_load_list_failing_takes_id_intersection(self):
        list_file = tempfile.NamedTemporaryFile()
        self.addCleanup(list_file.close)
        write_list(list_file, ['foo', 'quux', 'failing1'])
        # The extra tests - foo, quux - won't match known failures, and the
        # unlisted failure failing2 won't match the list.
        expected_ids = set(['failing1'])
        list_file.flush()
        ui, cmd = self.get_test_ui_and_cmd(
            options=[('load_list', list_file.name), ('failing', True)])
        cmd.repository_factory = memory.RepositoryFactory()
        self.setup_repo(cmd, ui)
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDOPTION\ntest_id_option=--load-list $IDFILE\n')
        params, capture_ids = self.capture_ids()
        self.useFixture(MonkeyPatch(
            'testrepository.testcommand.TestCommand.get_run_command',
            capture_ids))
        cmd_result = cmd.execute()
        self.assertEqual([
            ('results', Wildcard),
            ('summary', True, 0, -3, None, None, [('id', 1, None)])
            ], ui.outputs)
        self.assertEqual(0, cmd_result)
        self.assertEqual([Wildcard, expected_ids, [], None], params)

    def test_load_list_passes_ids(self):
        list_file = tempfile.NamedTemporaryFile()
        self.addCleanup(list_file.close)
        expected_ids = set(['foo', 'quux', 'bar'])
        write_list(list_file, expected_ids)
        list_file.flush()
        ui, cmd = self.get_test_ui_and_cmd(
            options=[('load_list', list_file.name)])
        cmd.repository_factory = memory.RepositoryFactory()
        self.setup_repo(cmd, ui)
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDOPTION\ntest_id_option=--load-list $IDFILE\n')
        params, capture_ids = self.capture_ids()
        self.useFixture(MonkeyPatch(
            'testrepository.testcommand.TestCommand.get_run_command',
            capture_ids))
        cmd_result = cmd.execute()
        self.assertEqual([
            ('results', Wildcard),
            ('summary', True, 0, -3, None, None, [('id', 1, None)])
            ], ui.outputs)
        self.assertEqual(0, cmd_result)
        self.assertEqual([Wildcard, expected_ids, [], None], params)

    def test_extra_options_passed_in(self):
        ui, cmd = self.get_test_ui_and_cmd(args=('--', 'bar', 'quux'))
        cmd.repository_factory = memory.RepositoryFactory()
        self.setup_repo(cmd, ui)
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDOPTION\ntest_id_option=--load-list $IDFILE\n')
        self.assertEqual(0, cmd.execute())
        expected_cmd = 'foo  bar quux'
        self.assertEqual([
            ('values', [('running', expected_cmd)]),
            ('popen', (expected_cmd,),
             {'shell': True, 'stdin': PIPE, 'stdout': PIPE}),
            ('results', Wildcard),
            ('summary', True, 0, -3, None, None, [('id', 1, None)])
            ], ui.outputs)

    def test_quiet_passed_down(self):
        ui, cmd = self.get_test_ui_and_cmd(options=[('quiet', True)])
        cmd.repository_factory = memory.RepositoryFactory()
        self.setup_repo(cmd, ui)
        self.set_config(
            '[DEFAULT]\ntest_command=foo\n')
        result = cmd.execute()
        expected_cmd = 'foo'
        self.assertEqual([
            ('values', [('running', expected_cmd)]),
            ('popen', (expected_cmd,),
             {'shell': True, 'stdin': PIPE, 'stdout': PIPE}),
            ], ui.outputs)
        self.assertEqual(0, result)

    def test_partial_passed_to_repo(self):
        ui, cmd = self.get_test_ui_and_cmd(
            options=[('quiet', True), ('partial', True)])
        cmd.repository_factory = memory.RepositoryFactory()
        self.setup_repo(cmd, ui)
        self.set_config(
            '[DEFAULT]\ntest_command=foo\n')
        result = cmd.execute()
        expected_cmd = 'foo'
        self.assertEqual([
            ('values', [('running', expected_cmd)]),
            ('popen', (expected_cmd,),
             {'shell': True, 'stdin': PIPE, 'stdout': PIPE}),
            ], ui.outputs)
        self.assertEqual(0, result)
        self.assertEqual(True,
            cmd.repository_factory.repos[ui.here].get_test_run(1)._partial)

    def test_load_failure_exposed(self):
        if v2_avail:
            buffer = BytesIO()
            stream = subunit.StreamResultToBytes(buffer)
            stream.status(test_id='foo', test_status='inprogress')
            stream.status(test_id='foo', test_status='fail')
            subunit_bytes = buffer.getvalue()
        else:
            subunit_bytes = b'test: foo\nfailure: foo\n'
        ui, cmd = self.get_test_ui_and_cmd(options=[('quiet', True),],
            proc_outputs=[subunit_bytes])
        cmd.repository_factory = memory.RepositoryFactory()
        self.setup_repo(cmd, ui)
        self.set_config('[DEFAULT]\ntest_command=foo\n')
        result = cmd.execute()
        cmd.repository_factory.repos[ui.here].get_test_run(1)
        self.assertEqual(1, result)

    def test_process_exit_code_nonzero_causes_synthetic_error_test(self):
        if v2_avail:
            buffer = BytesIO()
            stream = subunit.StreamResultToBytes(buffer)
            stream.status(test_id='foo', test_status='inprogress')
            stream.status(test_id='foo', test_status='success')
            subunit_bytes = buffer.getvalue()
        else:
            subunit_bytes = b'test: foo\nsuccess: foo\n'
        ui, cmd = self.get_test_ui_and_cmd(options=[('quiet', True),],
            proc_outputs=[subunit_bytes],
            proc_results=[2])
            # 2 is non-zero, and non-zero triggers the behaviour of exiting
            # with 1 - but we want to see that it doesn't pass-through the
            # value literally.
        cmd.repository_factory = memory.RepositoryFactory()
        self.setup_repo(cmd, ui)
        self.set_config('[DEFAULT]\ntest_command=foo\n')
        result = cmd.execute()
        self.assertEqual(1, result)
        run = cmd.repository_factory.repos[ui.here].get_test_run(1)
        self.assertEqual([Wildcard, 'Failure'],
            [outcome[0] for outcome in run._outcomes])

    def test_regex_test_filter(self):
        ui, cmd = self.get_test_ui_and_cmd(args=('ab.*cd', '--', 'bar', 'quux'))
        ui.proc_outputs = [_b('ab-cd\nefgh\n')]
        cmd.repository_factory = memory.RepositoryFactory()
        self.setup_repo(cmd, ui)
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDLIST $LISTOPT\n'
            'test_id_option=--load-list $IDFILE\n'
            'test_list_option=--list\n')
        params, capture_ids = self.capture_ids()
        self.useFixture(MonkeyPatch(
            'testrepository.testcommand.TestCommand.get_run_command',
            capture_ids))
        cmd_result = cmd.execute()
        self.assertEqual([
            ('results', Wildcard),
            ('summary', True, 0, -3, None, None, [('id', 1, None)])
            ], ui.outputs)
        self.assertEqual(0, cmd_result)
        self.assertThat(params[1], Equals(None))
        self.assertThat(
            params[2], MatchesListwise([Equals('bar'), Equals('quux')]))
        self.assertThat(params[3], MatchesListwise([Equals('ab.*cd')]))

    def test_regex_test_filter_with_explicit_ids(self):
        ui, cmd = self.get_test_ui_and_cmd(
            args=('g1', '--', 'bar', 'quux'),options=[('failing', True)])
        ui.proc_outputs = ['ab-cd\nefgh\n']
        cmd.repository_factory = memory.RepositoryFactory()
        self.setup_repo(cmd, ui)
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDLIST $LISTOPT\n'
            'test_id_option=--load-list $IDFILE\n'
            'test_list_option=--list\n')
        params, capture_ids = self.capture_ids()
        self.useFixture(MonkeyPatch(
            'testrepository.testcommand.TestCommand.get_run_command',
            capture_ids))
        cmd_result = cmd.execute()
        self.assertEqual([
            ('results', Wildcard),
            ('summary', True, 0, -3, None, None, [('id', 1, None)])
            ], ui.outputs)
        self.assertEqual(0, cmd_result)
        self.assertThat(params[1], Equals(['failing1', 'failing2']))
        self.assertThat(
            params[2], MatchesListwise([Equals('bar'), Equals('quux')]))
        self.assertThat(params[3], MatchesListwise([Equals('g1')]))

    def test_until_failure(self):
        ui, cmd = self.get_test_ui_and_cmd(options=[('until_failure', True)])
        if v2_avail:
            buffer = BytesIO()
            stream = subunit.StreamResultToBytes(buffer)
            stream.status(test_id='foo', test_status='inprogress')
            stream.status(test_id='foo', test_status='success')
            subunit_bytes1 = buffer.getvalue()
            buffer.seek(0)
            buffer.truncate()
            stream.status(test_id='foo', test_status='inprogress')
            stream.status(test_id='foo', test_status='fail')
            subunit_bytes2 = buffer.getvalue()
        else:
            subunit_bytes1 = b'test: foo\nsuccess: foo\n'
            subunit_bytes2 = b'test: foo\nfailure: foo\n'
        ui.proc_outputs = [
            subunit_bytes1, # stream one, works
            subunit_bytes2, # stream two, fails
            ]
        ui.require_proc_stdout = True
        cmd.repository_factory = memory.RepositoryFactory()
        self.setup_repo(cmd, ui)
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDLIST $LISTOPT\n'
            'test_id_option=--load-list $IDFILE\n'
            'test_list_option=--list\n')
        cmd_result = cmd.execute()
        expected_cmd = 'foo  '
        self.assertEqual([
            ('values', [('running', expected_cmd)]),
            ('popen', (expected_cmd,),
             {'shell': True, 'stdin': PIPE, 'stdout': PIPE}),
            ('results', Wildcard),
            ('summary', True, 1, -2, Wildcard, None, [('id', 1, None)]),
            ('values', [('running', expected_cmd)]),
            ('popen', (expected_cmd,),
             {'shell': True, 'stdin': PIPE, 'stdout': PIPE}),
            ('results', Wildcard),
            ('summary', False, 1, 0, Wildcard, Wildcard,
             [('id', 2, None), ('failures', 1, 1)])
            ], ui.outputs)
        self.assertEqual(1, cmd_result)

    def test_failure_no_tests_run_when_no_failures_failures(self):
        ui, cmd = self.get_test_ui_and_cmd(options=[('failing', True)])
        cmd.repository_factory = memory.RepositoryFactory()
        self.setup_repo(cmd, ui, failures=False)
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDOPTION\ntest_id_option=--load-list $IDFILE\n')
        cmd.command_factory = FakeTestCommand
        result = cmd.execute()
        self.assertEqual([
            ('results', Wildcard),
            ('summary', True, 0, -1, None, None, [('id', 1, None)])
            ], ui.outputs)
        self.assertEqual(0, result)


def read_all(stream):
    return stream.read()


def read_single(stream):
    return stream.read(1)


def readline(stream):
    return stream.readline()


def readlines(stream):
    return _b('').join(stream.readlines())


def accumulate(stream, reader):
    accumulator = []
    content = reader(stream)
    while content:
        accumulator.append(content)
        content = reader(stream)
    return _b('').join(accumulator)


class TestReturnCodeToSubunit(ResourcedTestCase):

    scenarios = multiply_scenarios(
        [('readdefault', dict(reader=read_all)),
         ('readsingle', dict(reader=read_single)),
         ('readline', dict(reader=readline)),
         ('readlines', dict(reader=readlines)),
         ],
        [('noeol', dict(stdout=_b('foo\nbar'))),
         ('trailingeol', dict(stdout=_b('foo\nbar\n')))])

    def test_returncode_0_no_change(self):
        proc = ProcessModel(None)
        proc.stdout.write(self.stdout)
        proc.stdout.seek(0)
        stream = run.ReturnCodeToSubunit(proc)
        content = accumulate(stream, self.reader)
        self.assertEqual(self.stdout, content)

    def test_returncode_nonzero_fail_appended_to_content(self):
        proc = ProcessModel(None)
        proc.stdout.write(self.stdout)
        proc.stdout.seek(0)
        proc.returncode = 1
        stream = run.ReturnCodeToSubunit(proc)
        content = accumulate(stream, self.reader)
        if v2_avail:
            buffer = BytesIO()
            buffer.write(b'foo\nbar\n')
            stream = subunit.StreamResultToBytes(buffer)
            stream.status(test_id='process-returncode', test_status='fail',
                file_name='traceback', mime_type='test/plain;charset=utf8',
                file_bytes=b'returncode 1')
            expected_content = buffer.getvalue()
        else:
            expected_content = _b('foo\nbar\ntest: process-returncode\n'
                'failure: process-returncode [\n returncode 1\n]\n')
        self.assertEqual(expected_content, content)
