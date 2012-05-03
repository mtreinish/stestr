#
# Copyright (c) 2009 Testrepository Contributors
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

"""Tests for the load command."""

from datetime import datetime

from subunit import iso8601

import testtools
from testtools.content import text_content
from testtools.matchers import MatchesException
from testtools.tests.helpers import LoggingResult

from testrepository.commands import load
from testrepository.ui.model import UI
from testrepository.tests import (
    ResourcedTestCase,
    StubTestCommand,
    Wildcard,
    )
from testrepository.tests.test_repository import RecordingRepositoryFactory
from testrepository.tests.repository.test_file import HomeDirTempDir
from testrepository.repository import memory, RepositoryNotFound


class TestCommandLoad(ResourcedTestCase):

    def test_load_loads_subunit_stream_to_default_repository(self):
        ui = UI([('subunit', '')])
        cmd = load.load(ui)
        ui.set_command(cmd)
        calls = []
        cmd.repository_factory = RecordingRepositoryFactory(calls,
            memory.RepositoryFactory())
        repo = cmd.repository_factory.initialise(ui.here)
        del calls[:]
        cmd.execute()
        # Right repo
        self.assertEqual([('open', ui.here)], calls)
        # Stream consumed
        self.assertFalse('subunit' in ui.input_streams)
        # Results loaded
        self.assertEqual(1, repo.count())

    def test_load_initialises_repo_if_doesnt_exist_and_init_forced(self):
        ui = UI([('subunit', '')], options=[('force_init', True)])
        cmd = load.load(ui)
        ui.set_command(cmd)
        calls = []
        cmd.repository_factory = RecordingRepositoryFactory(calls,
            memory.RepositoryFactory())
        del calls[:]
        cmd.execute()
        self.assertEqual([('open', ui.here), ('initialise', ui.here)], calls)

    def test_load_errors_if_repo_doesnt_exist(self):
        ui = UI([('subunit', '')])
        cmd = load.load(ui)
        ui.set_command(cmd)
        calls = []
        cmd.repository_factory = RecordingRepositoryFactory(calls,
            memory.RepositoryFactory())
        del calls[:]
        cmd.execute()
        self.assertEqual([('open', ui.here)], calls)
        self.assertEqual([('error', Wildcard)], ui.outputs)
        self.assertThat(
            ui.outputs[0][1], MatchesException(RepositoryNotFound('memory:')))

    def test_load_returns_0_normally(self):
        ui = UI([('subunit', '')])
        cmd = load.load(ui)
        ui.set_command(cmd)
        cmd.repository_factory = memory.RepositoryFactory()
        cmd.repository_factory.initialise(ui.here)
        self.assertEqual(0, cmd.execute())

    def test_load_returns_1_on_failed_stream(self):
        ui = UI([('subunit', 'test: foo\nfailure: foo\n')])
        cmd = load.load(ui)
        ui.set_command(cmd)
        cmd.repository_factory = memory.RepositoryFactory()
        cmd.repository_factory.initialise(ui.here)
        self.assertEqual(1, cmd.execute())

    def test_load_new_shows_test_failures(self):
        ui = UI([('subunit', 'test: foo\nfailure: foo\n')])
        cmd = load.load(ui)
        ui.set_command(cmd)
        cmd.repository_factory = memory.RepositoryFactory()
        cmd.repository_factory.initialise(ui.here)
        self.assertEqual(1, cmd.execute())
        self.assertEqual(
            [('summary', False, 1, None, Wildcard, None,
              [('id', 0, None), ('failures', 1, None)])],
            ui.outputs[1:])

    def test_load_new_shows_test_failure_details(self):
        ui = UI([('subunit', 'test: foo\nfailure: foo [\narg\n]\n')])
        cmd = load.load(ui)
        ui.set_command(cmd)
        cmd.repository_factory = memory.RepositoryFactory()
        cmd.repository_factory.initialise(ui.here)
        self.assertEqual(1, cmd.execute())
        suite = ui.outputs[0][1]
        self.assertEqual([
            ('results', Wildcard),
            ('summary', False, 1, None, Wildcard, None,
             [('id', 0, None), ('failures', 1, None)])],
            ui.outputs)
        result = testtools.TestResult()
        result.startTestRun()
        try:
            suite.run(result)
        finally:
            result.stopTestRun()
        self.assertEqual(1, result.testsRun)
        self.assertEqual(1, len(result.failures))

    def test_load_new_shows_test_skips(self):
        ui = UI([('subunit', 'test: foo\nskip: foo\n')])
        cmd = load.load(ui)
        ui.set_command(cmd)
        cmd.repository_factory = memory.RepositoryFactory()
        cmd.repository_factory.initialise(ui.here)
        self.assertEqual(0, cmd.execute())
        self.assertEqual(
            [('results', Wildcard),
             ('summary', True, 1, None, Wildcard, None,
              [('id', 0, None), ('skips', 1, None)])],
            ui.outputs)

    def test_load_new_shows_test_summary_no_tests(self):
        ui = UI([('subunit', '')])
        cmd = load.load(ui)
        ui.set_command(cmd)
        cmd.repository_factory = memory.RepositoryFactory()
        cmd.repository_factory.initialise(ui.here)
        self.assertEqual(0, cmd.execute())
        self.assertEqual(
            [('results', Wildcard),
             ('summary', True, 0, None, None, None, [('id', 0, None)])],
            ui.outputs)

    def test_load_quiet_shows_nothing(self):
        ui = UI([('subunit', '')], [('quiet', True)])
        cmd = load.load(ui)
        ui.set_command(cmd)
        cmd.repository_factory = memory.RepositoryFactory()
        cmd.repository_factory.initialise(ui.here)
        self.assertEqual(0, cmd.execute())
        self.assertEqual([], ui.outputs)

    def test_partial_passed_to_repo(self):
        ui = UI([('subunit', '')], [('quiet', True), ('partial', True)])
        cmd = load.load(ui)
        ui.set_command(cmd)
        cmd.repository_factory = memory.RepositoryFactory()
        cmd.repository_factory.initialise(ui.here)
        self.assertEqual(0, cmd.execute())
        self.assertEqual([], ui.outputs)
        self.assertEqual(True,
            cmd.repository_factory.repos[ui.here].get_test_run(0)._partial)

    def test_load_timed_run(self):
        ui = UI(
            [('subunit',
              ('time: 2011-01-01 00:00:01.000000Z\n'
               'test: foo\n'
               'time: 2011-01-01 00:00:03.000000Z\n'
               'success: foo\n'
               'time: 2011-01-01 00:00:06.000000Z\n'))])
        cmd = load.load(ui)
        ui.set_command(cmd)
        cmd.repository_factory = memory.RepositoryFactory()
        cmd.repository_factory.initialise(ui.here)
        self.assertEqual(0, cmd.execute())
        # Note that the time here is 2.0, the difference between first and
        # second time: directives. That's because 'load' uses a
        # ThreadsafeForwardingResult (via ConcurrentTestSuite) that suppresses
        # time information not involved in the start or stop of a test.
        self.assertEqual(
            [('summary', True, 1, None, 2.0, None, [('id', 0, None)])],
            ui.outputs[1:])

    def test_load__wrap_result_inserts_worker_id_tag(self):
        # The load command uses a result wrapper that tags each test with the
        # ID of the worker that executed the test.
        log = []
        result = load._wrap_result(LoggingResult(log), 99)
        result.startTestRun()
        result.startTest(self)
        result.addUnexpectedSuccess(self)
        result.stopTest(self)
        result.stopTestRun()
        # Even though no tag data was provided above, the test has been tagged
        # with the worker ID.
        self.assertIn(('tags', set(['worker-99']), set([])), log)

    def test_load_second_run(self):
        # If there's a previous run in the database, then show information
        # about the high level differences in the test run: how many more
        # tests, how many more failures, how much longer it takes.
        ui = UI(
            [('subunit',
              ('time: 2011-01-02 00:00:01.000000Z\n'
               'test: foo\n'
               'time: 2011-01-02 00:00:03.000000Z\n'
               'error: foo\n'
               'time: 2011-01-02 00:00:05.000000Z\n'
               'test: bar\n'
               'time: 2011-01-02 00:00:07.000000Z\n'
               'error: bar\n'
               ))])
        cmd = load.load(ui)
        ui.set_command(cmd)
        cmd.repository_factory = memory.RepositoryFactory()
        repo = cmd.repository_factory.initialise(ui.here)
        # XXX: Circumvent the AutoTimingTestResultDecorator so we can get
        # predictable times, rather than ones based on the system
        # clock. (Would normally expect to use repo.get_inserter())
        inserter = repo._get_inserter(False)
        # Insert a run with different results.
        inserter.startTestRun()
        inserter.time(datetime(2011, 1, 1, 0, 0, 1, tzinfo=iso8601.Utc()))
        inserter.startTest(self)
        inserter.time(datetime(2011, 1, 1, 0, 0, 10, tzinfo=iso8601.Utc()))
        inserter.addError(self, details={'traceback': text_content('foo')})
        inserter.stopTest(self)
        inserter.stopTestRun()
        self.assertEqual(1, cmd.execute())
        # Note that the time here is 2.0, the difference between first and
        # second time: directives. That's because 'load' uses a
        # ThreadsafeForwardingResult (via ConcurrentTestSuite) that suppresses
        # time information not involved in the start or stop of a test.
        self.assertEqual(
            [('summary', False, 2, 1, 6.0, -3.0,
              [('id', 1, None), ('failures', 2, 1)])],
            ui.outputs[1:])

    def test_grabs_TestCommand_result(self):
        ui = UI([('subunit', '')])
        cmd = load.load(ui)
        ui.set_command(cmd)
        cmd.repository_factory = memory.RepositoryFactory()
        cmd.repository_factory.initialise(ui.here)
        cmd.command_factory = StubTestCommand()
        cmd.execute()
        self.assertEqual(
            [('startTestRun',), ('stopTestRun',)],
            cmd.command_factory.results[0]._events)
