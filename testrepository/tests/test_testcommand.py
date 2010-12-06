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

"""Tests for the testcommand module."""

import os.path

from fixtures import Fixture
from testtools.matchers import MatchesException, Raises

from testrepository.commands import run
from testrepository.ui.model import UI
from testrepository.repository import memory
from testrepository.testcommand import TestCommand
from testrepository.tests import ResourcedTestCase
from testrepository.tests.stubpackage import TempDirResource
from testrepository.tests.test_repository import make_test


class FakeTestCommand(TestCommand):

    def __init__(self, ui):
        TestCommand.__init__(self, ui)
        self.oldschool = True


class TestTestCommand(ResourcedTestCase):

    resources = [('tempdir', TempDirResource())]

    def get_test_ui_and_cmd(self, options=(), args=()):
        self.dirty()
        ui = UI(options=options, args=args)
        ui.here = self.tempdir
        return ui, TestCommand(ui)

    def get_test_ui_and_cmd2(self, options=(), args=()):
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

    def test_takes_ui(self):
        ui = UI()
        ui.here = self.tempdir
        command = TestCommand(ui)
        self.assertEqual(command.ui, ui)

    def test_get_run_command_no_config_file_errors(self):
        ui, command = self.get_test_ui_and_cmd()
        self.assertThat(command.get_run_command,
            Raises(MatchesException(ValueError('No .testr.conf config file'))))

    def test_get_run_command_no_config_settings_errors(self):
        ui, command = self.get_test_ui_and_cmd()
        self.set_config('')
        self.assertThat(command.get_run_command,
            Raises(MatchesException(ValueError(
            'No test_command option present in .testr.conf'))))

    def test_get_run_command_returns_fixture_makes_IDFILE(self):
        ui, command = self.get_test_ui_and_cmd()
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDOPTION\ntest_id_option=--load-list $IDFILE\n')
        fixture = command.get_run_command(['failing', 'alsofailing'])
        try:
            fixture.setUp()
            list_file_path = fixture.list_file_name
            source = open(list_file_path, 'rb')
            try:
                list_file_content = source.read()
            finally:
                source.close()
            self.assertEqual("failing\nalsofailing\n", list_file_content)
        finally:
            fixture.cleanUp()
        self.assertFalse(os.path.exists(list_file_path))

    def test_get_run_command_IDFILE_variable_setting(self):
        ui, command = self.get_test_ui_and_cmd()
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDOPTION\ntest_id_option=--load-list $IDFILE\n')
        fixture = self.useFixture(
            command.get_run_command(['failing', 'alsofailing']))
        expected_cmd = 'foo --load-list %s' % fixture.list_file_name
        self.assertEqual(expected_cmd, fixture.cmd)

    def test_get_run_command_IDLIST_variable_setting(self):
        ui, command = self.get_test_ui_and_cmd()
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDLIST\n')
        fixture = self.useFixture(
            command.get_run_command(['failing', 'alsofailing']))
        expected_cmd = 'foo failing alsofailing'
        self.assertEqual(expected_cmd, fixture.cmd)

    def test_get_run_command_IDLIST_default_is_empty(self):
        ui, command = self.get_test_ui_and_cmd()
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDLIST\n')
        fixture = self.useFixture(command.get_run_command())
        expected_cmd = 'foo '
        self.assertEqual(expected_cmd, fixture.cmd)

    def test_get_run_command_IDLIST_default_passed_normally(self):
        ui, command = self.get_test_ui_and_cmd()
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDLIST\ntest_id_list_default=whoo yea\n')
        fixture = self.useFixture(command.get_run_command())
        expected_cmd = 'foo whoo yea'
        self.assertEqual(expected_cmd, fixture.cmd)

    def test_IDOPTION_evalutes_empty_string_no_ids(self):
        ui, command = self.get_test_ui_and_cmd()
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDOPTION\ntest_id_option=--load-list $IDFILE\n')
        fixture = self.useFixture(command.get_run_command())
        expected_cmd = 'foo '
        self.assertEqual(expected_cmd, fixture.cmd)

    def test_extra_args_passed_in(self):
        ui, command = self.get_test_ui_and_cmd()
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDOPTION\ntest_id_option=--load-list $IDFILE\n')
        fixture = self.useFixture(command.get_run_command(
            testargs=('bar', 'quux')))
        expected_cmd = 'foo  bar quux'
        self.assertEqual(expected_cmd, fixture.cmd)

    def test_list_tests_cmd(self):
        ui, command = self.get_test_ui_and_cmd()
        self.set_config(
            '[DEFAULT]\ntest_command=foo $LISTOPT $IDLIST\ntest_id_list_default=whoo yea\n'
            'test_list_option=--list\n')
        fixture = self.useFixture(command.get_run_command())
        expected_cmd = 'foo --list whoo yea'
        self.assertEqual(expected_cmd, fixture.list_cmd)

    def test_list_tests_parsing(self):
        ui, command = self.get_test_ui_and_cmd()
        ui.proc_outputs = ['returned\nids\n']
        self.set_config(
            '[DEFAULT]\ntest_command=foo $LISTOPT $IDLIST\ntest_id_list_default=whoo yea\n'
            'test_list_option=--list\n')
        fixture = self.useFixture(command.get_run_command())
        self.assertEqual(set(['returned', 'ids']), set(fixture.list_tests()))
