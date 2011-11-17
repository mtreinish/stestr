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

from testtools.matchers import MatchesException

from testrepository.commands import run
from testrepository.ui.model import UI
from testrepository.repository import memory
from testrepository.tests import ResourcedTestCase, Wildcard
from testrepository.tests.stubpackage import TempDirResource
from testrepository.tests.test_testcommand import FakeTestCommand
from testrepository.tests.test_repository import make_test


class TestCommand(ResourcedTestCase):

    resources = [('tempdir', TempDirResource())]

    def get_test_ui_and_cmd(self, options=(), args=()):
        self.dirty()
        ui = UI(options=options, args=args)
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
