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
from testtools.testresult.doubles import ExtendedTestResult

from testrepository.commands import run
from testrepository.ui.model import UI
from testrepository.repository import memory
from testrepository.testcommand import TestCommand
from testrepository.tests import ResourcedTestCase
from testrepository.tests.stubpackage import TempDirResource
from testrepository.tests.test_repository import make_test, run_timed


class FakeTestCommand(TestCommand):

    def __init__(self, ui, repo):
        TestCommand.__init__(self, ui, repo)
        self.oldschool = True


class TestTestCommand(ResourcedTestCase):

    resources = [('tempdir', TempDirResource())]

    def get_test_ui_and_cmd(self, options=(), args=(), repository=None):
        self.dirty()
        ui = UI(options=options, args=args)
        ui.here = self.tempdir
        return ui, TestCommand(ui, repository)

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
        command = TestCommand(ui, None)
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

    def test_partition_tests_smoke(self):
        repo = memory.RepositoryFactory().initialise('memory:')
        # Seed with 1 slow and 2 tests making up 2/3 the time.
        result = repo.get_inserter()
        result.startTestRun()
        run_timed("slow", 3, result)
        run_timed("fast1", 1, result)
        run_timed("fast2", 1, result)
        result.stopTestRun()
        ui, command = self.get_test_ui_and_cmd(repository=repo)
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDLIST\n')
        fixture = self.useFixture(command.get_run_command())
        # partitioning by two generates 'slow' and the two fast ones as partitions
        # flushed out by equal numbers of unknown duration tests.
        test_ids = frozenset(['slow', 'fast1', 'fast2', 'unknown1', 'unknown2',
            'unknown3', 'unknown4'])
        partitions = fixture.partition_tests(test_ids, 2)
        self.assertTrue('slow' in partitions[0])
        self.assertFalse('fast1' in partitions[0])
        self.assertFalse('fast2' in partitions[0])
        self.assertFalse('slow' in partitions[1])
        self.assertTrue('fast1' in partitions[1])
        self.assertTrue('fast2' in partitions[1])
        self.assertEqual(3, len(partitions[0]))
        self.assertEqual(4, len(partitions[1]))

    def test_partition_tests_914359(self):
        # When two partitions have the same duration, timed tests should be
        # appended to the shortest partition. In theory this doesn't matter,
        # but in practice, if a test is recorded with 0 duration (e.g. due to a
        # bug), it is better to have them split out rather than all in one
        # partition. 0 duration tests are unlikely to really be 0 duration.
        repo = memory.RepositoryFactory().initialise('memory:')
        # Seed with two 0-duration tests.
        result = repo.get_inserter()
        result.startTestRun()
        run_timed("zero1", 0, result)
        run_timed("zero2", 0, result)
        result.stopTestRun()
        ui, command = self.get_test_ui_and_cmd(repository=repo)
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDLIST\n')
        fixture = self.useFixture(command.get_run_command())
        # partitioning by two should generate two one-entry partitions.
        test_ids = frozenset(['zero1', 'zero2'])
        partitions = fixture.partition_tests(test_ids, 2)
        self.assertEqual(1, len(partitions[0]))
        self.assertEqual(1, len(partitions[1]))

    def test_filter_tags_parsing(self):
        ui, command = self.get_test_ui_and_cmd()
        self.set_config('[DEFAULT]\nfilter_tags=foo bar\n')
        self.assertEqual(set(['foo', 'bar']), command.get_filter_tags())

    def test_make_result(self):
        # Just a simple 'the dots are joined' test. More later.
        ui, command = self.get_test_ui_and_cmd()
        log = ExtendedTestResult()
        result = command.make_result(log)
        result.startTestRun()
        result.stopTestRun()
        self.assertEqual([('startTestRun',), ('stopTestRun',)], log._events)
