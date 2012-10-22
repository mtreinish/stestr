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

import os.path
from subprocess import PIPE

from subunit import RemotedTestCase
from testscenarios.scenarios import multiply_scenarios
from testtools.matchers import (
    Equals,
    MatchesException,
    MatchesListwise,
    )

from testrepository.commands import run
from testrepository.ui.model import UI, ProcessModel
from testrepository.repository import memory
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

    def set_config(self, bytes):
        stream = file(self.config_path(), 'wb')
        try:
            stream.write(bytes)
        finally:
            stream.close()

    def setup_repo(self, cmd, ui):
        repo = cmd.repository_factory.initialise(ui.here)
        inserter = repo.get_inserter()
        inserter.startTestRun()
        make_test('passing', True).run(inserter)
        make_test('failing', False).run(inserter)
        inserter.stopTestRun()

    def test_no_config_file_errors(self):
        ui, cmd = self.get_test_ui_and_cmd()
        repo = cmd.repository_factory.initialise(ui.here)
        self.assertEqual(3, cmd.execute())
        self.assertEqual(1, len(ui.outputs))
        self.assertEqual('error', ui.outputs[0][0])
        self.assertThat(ui.outputs[0][1],
            MatchesException(ValueError('No .testr.conf config file')))

    def test_no_config_settings_errors(self):
        ui, cmd = self.get_test_ui_and_cmd()
        repo = cmd.repository_factory.initialise(ui.here)
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
            ('summary', True, 0, -2, None, None, [('id', 1, None)])
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
        expected_cmd = 'foo failing'
        self.assertEqual([
            ('values', [('running', expected_cmd)]),
            ('popen', (expected_cmd,),
             {'shell': True, 'stdin': PIPE, 'stdout': PIPE}),
            ('results', Wildcard),
            ('summary', True, 0, -2, None, None, [('id', 1, None)]),
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
            ('summary', True, 0, -2, None, None, [('id', 1, None)])
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
            ('summary', True, 0, -2, None, None, [('id', 1, None)])
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
            ('summary', True, 0, -2, None, None, [('id', 1, None)]),
            ], ui.outputs)

    def test_extra_options_passed_in(self):
        ui, cmd = self.get_test_ui_and_cmd(args=('bar', 'quux'))
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
            ('summary', True, 0, -2, None, None, [('id', 1, None)])
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
        ui, cmd = self.get_test_ui_and_cmd(options=[('quiet', True),],
            proc_outputs=['test: foo\nfailure: foo\n'])
        cmd.repository_factory = memory.RepositoryFactory()
        self.setup_repo(cmd, ui)
        self.set_config('[DEFAULT]\ntest_command=foo\n')
        result = cmd.execute()
        run = cmd.repository_factory.repos[ui.here].get_test_run(1)
        self.assertEqual(1, result)

    def test_process_exit_code_nonzero_causes_synthetic_error_test(self):
        ui, cmd = self.get_test_ui_and_cmd(options=[('quiet', True),],
            proc_outputs=['test: foo\nsuccess: foo\n'],
            proc_results=[2])
            # 2 is non-zero, and non-zero triggers the behaviour of exiting
            # with 1 - but we want to see that it doesn't pass-through the
            # value literally.
        cmd.repository_factory = memory.RepositoryFactory()
        self.setup_repo(cmd, ui)
        self.set_config('[DEFAULT]\ntest_command=foo\n')
        result = cmd.execute()
        expected_cmd = 'foo'
        self.assertEqual(1, result)
        run = cmd.repository_factory.repos[ui.here].get_test_run(1)
        self.assertEqual([
            Wildcard,
            ('Error', RemotedTestCase('process-returncode'), Wildcard)],
            run._outcomes)


def read_all(stream):
    return stream.read()


def read_single(stream):
    return stream.read(1)


def readline(stream):
    return stream.readline()


def readlines(stream):
    return ''.join(stream.readlines())


def accumulate(stream, reader):
    accumulator = []
    content = reader(stream)
    while content:
        accumulator.append(content)
        content = reader(stream)
    return ''.join(accumulator)


class TestReturnCodeToSubunit(ResourcedTestCase):

    scenarios = multiply_scenarios(
        [('readdefault', dict(reader=read_all)),
         ('readsingle', dict(reader=read_single)),
         ('readline', dict(reader=readline)),
         ('readlines', dict(reader=readlines)),
         ],
        [('noeol', dict(stdout='foo\nbar')),
         ('trailingeol', dict(stdout='foo\nbar\n'))])

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
        self.assertEqual(
            'foo\nbar\ntest: process-returncode\n'
            'error: process-returncode [\n returncode 1\n]\n',
            content)
