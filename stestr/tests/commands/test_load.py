#
# Copyright (c) 2009, 2012 Testrepository Contributors
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

from datetime import datetime, timedelta
from io import BytesIO
from tempfile import NamedTemporaryFile

from extras import try_import
v2_avail = try_import('subunit.ByteStreamToStreamResult')
import subunit
from subunit import iso8601

import testtools
from testtools.compat import _b
from testtools.content import text_content
from testtools.matchers import MatchesException
from testtools.tests.helpers import LoggingResult

from stestr.commands import load
from stestr.ui.model import UI
from stestr.tests import (
    ResourcedTestCase,
    StubTestCommand,
    Wildcard,
    )
from stestr.tests.test_repository import RecordingRepositoryFactory
from stestr.tests.repository.test_file import HomeDirTempDir
from stestr.repository import memory, RepositoryNotFound


class TestCommandLoad(ResourcedTestCase):

    def test_load_loads_subunit_stream_to_default_repository(self):
        ui = UI([('subunit', _b(''))])
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

    def test_load_loads_named_file_if_given(self):
        datafile = NamedTemporaryFile()
        self.addCleanup(datafile.close)
        ui = UI([('subunit', _b(''))], args=[datafile.name])
        cmd = load.load(ui)
        ui.set_command(cmd)
        calls = []
        cmd.repository_factory = RecordingRepositoryFactory(calls,
            memory.RepositoryFactory())
        repo = cmd.repository_factory.initialise(ui.here)
        del calls[:]
        self.assertEqual(0, cmd.execute())
        # Right repo
        self.assertEqual([('open', ui.here)], calls)
        # Stream not consumed - otherwise CLI would block when someone runs
        # 'testr load foo'. XXX: Be nice if we could declare that the argument,
        # which is a path, is to be an input stream.
        self.assertTrue('subunit' in ui.input_streams)
        # Results loaded
        self.assertEqual(1, repo.count())

    def test_load_initialises_repo_if_doesnt_exist_and_init_forced(self):
        ui = UI([('subunit', _b(''))], options=[('force_init', True)])
        cmd = load.load(ui)
        ui.set_command(cmd)
        calls = []
        cmd.repository_factory = RecordingRepositoryFactory(calls,
            memory.RepositoryFactory())
        del calls[:]
        cmd.execute()
        self.assertEqual([('open', ui.here), ('initialise', ui.here)], calls)

    def test_load_errors_if_repo_doesnt_exist(self):
        ui = UI([('subunit', _b(''))])
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
        ui = UI([('subunit', _b(''))])
        cmd = load.load(ui)
        ui.set_command(cmd)
        cmd.repository_factory = memory.RepositoryFactory()
        cmd.repository_factory.initialise(ui.here)
        self.assertEqual(0, cmd.execute())

    def test_load_returns_1_on_failed_stream(self):
        if v2_avail:
            buffer = BytesIO()
            stream = subunit.StreamResultToBytes(buffer)
            stream.status(test_id='foo', test_status='inprogress')
            stream.status(test_id='foo', test_status='fail')
            subunit_bytes = buffer.getvalue()
        else:
            subunit_bytes = _b('test: foo\nfailure: foo\n')
        ui = UI([('subunit', subunit_bytes)])
        cmd = load.load(ui)
        ui.set_command(cmd)
        cmd.repository_factory = memory.RepositoryFactory()
        cmd.repository_factory.initialise(ui.here)
        self.assertEqual(1, cmd.execute())

    def test_load_new_shows_test_failures(self):
        if v2_avail:
            buffer = BytesIO()
            stream = subunit.StreamResultToBytes(buffer)
            stream.status(test_id='foo', test_status='inprogress')
            stream.status(test_id='foo', test_status='fail')
            subunit_bytes = buffer.getvalue()
        else:
            subunit_bytes = b'test: foo\nfailure: foo\n'
        ui = UI([('subunit', subunit_bytes)])
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
        if v2_avail:
            buffer = BytesIO()
            stream = subunit.StreamResultToBytes(buffer)
            stream.status(test_id='foo', test_status='inprogress')
            stream.status(test_id='foo', test_status='fail',
                file_name="traceback", mime_type='text/plain;charset=utf8',
                file_bytes=b'arg\n')
            subunit_bytes = buffer.getvalue()
        else:
            subunit_bytes = b'test: foo\nfailure: foo [\narg\n]\n'
        ui = UI([('subunit', subunit_bytes)])
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
        result = testtools.StreamSummary()
        result.startTestRun()
        try:
            suite.run(result)
        finally:
            result.stopTestRun()
        self.assertEqual(1, result.testsRun)
        self.assertEqual(1, len(result.errors))

    def test_load_new_shows_test_skips(self):
        if v2_avail:
            buffer = BytesIO()
            stream = subunit.StreamResultToBytes(buffer)
            stream.status(test_id='foo', test_status='inprogress')
            stream.status(test_id='foo', test_status='skip')
            subunit_bytes = buffer.getvalue()
        else:
            subunit_bytes = b'test: foo\nskip: foo\n'
        ui = UI([('subunit', subunit_bytes)])
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
        ui = UI([('subunit', _b(''))])
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
        ui = UI([('subunit', _b(''))], [('quiet', True)])
        cmd = load.load(ui)
        ui.set_command(cmd)
        cmd.repository_factory = memory.RepositoryFactory()
        cmd.repository_factory.initialise(ui.here)
        self.assertEqual(0, cmd.execute())
        self.assertEqual([], ui.outputs)

    def test_load_abort_over_interactive_stream(self):
        ui = UI([('subunit', b''), ('interactive', b'a\n')])
        cmd = load.load(ui)
        ui.set_command(cmd)
        cmd.repository_factory = memory.RepositoryFactory()
        cmd.repository_factory.initialise(ui.here)
        ret = cmd.execute()
        self.assertEqual(
            [('results', Wildcard),
             ('summary', False, 1, None, None, None,
                [('id', 0, None), ('failures', 1, None)])],
            ui.outputs)
        self.assertEqual(1, ret)

    def test_partial_passed_to_repo(self):
        ui = UI([('subunit', _b(''))], [('quiet', True), ('partial', True)])
        cmd = load.load(ui)
        ui.set_command(cmd)
        cmd.repository_factory = memory.RepositoryFactory()
        cmd.repository_factory.initialise(ui.here)
        retcode = cmd.execute()
        self.assertEqual([], ui.outputs)
        self.assertEqual(0, retcode)
        self.assertEqual(True,
            cmd.repository_factory.repos[ui.here].get_test_run(0)._partial)

    def test_load_timed_run(self):
        if v2_avail:
            buffer = BytesIO()
            stream = subunit.StreamResultToBytes(buffer)
            time = datetime(2011, 1, 1, 0, 0, 1, tzinfo=iso8601.Utc())
            stream.status(test_id='foo', test_status='inprogress', timestamp=time)
            stream.status(test_id='foo', test_status='success',
                timestamp=time+timedelta(seconds=2))
            timed_bytes = buffer.getvalue()
        else:
            timed_bytes = _b('time: 2011-01-01 00:00:01.000000Z\n'
               'test: foo\n'
               'time: 2011-01-01 00:00:03.000000Z\n'
               'success: foo\n'
               'time: 2011-01-01 00:00:06.000000Z\n')
        ui = UI(
            [('subunit', timed_bytes)])
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

    def test_load_second_run(self):
        # If there's a previous run in the database, then show information
        # about the high level differences in the test run: how many more
        # tests, how many more failures, how much longer it takes.
        if v2_avail:
            buffer = BytesIO()
            stream = subunit.StreamResultToBytes(buffer)
            time = datetime(2011, 1, 2, 0, 0, 1, tzinfo=iso8601.Utc())
            stream.status(test_id='foo', test_status='inprogress', timestamp=time)
            stream.status(test_id='foo', test_status='fail',
                timestamp=time+timedelta(seconds=2))
            stream.status(test_id='bar', test_status='inprogress',
                timestamp=time+timedelta(seconds=4))
            stream.status(test_id='bar', test_status='fail',
                timestamp=time+timedelta(seconds=6))
            timed_bytes = buffer.getvalue()
        else:
            timed_bytes = _b('time: 2011-01-02 00:00:01.000000Z\n'
               'test: foo\n'
               'time: 2011-01-02 00:00:03.000000Z\n'
               'error: foo\n'
               'time: 2011-01-02 00:00:05.000000Z\n'
               'test: bar\n'
               'time: 2011-01-02 00:00:07.000000Z\n'
               'error: bar\n')
        ui = UI(
            [('subunit', timed_bytes)])
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
        inserter.status(test_id=self.id(), test_status='inprogress',
            timestamp=datetime(2011, 1, 1, 0, 0, 1, tzinfo=iso8601.Utc()))
        inserter.status(test_id=self.id(), test_status='fail',
            timestamp=datetime(2011, 1, 1, 0, 0, 10, tzinfo=iso8601.Utc()))
        inserter.stopTestRun()
        self.assertEqual(1, cmd.execute())
        self.assertEqual(
            [('summary', False, 2, 1, 6.0, -3.0,
              [('id', 1, None), ('failures', 2, 1)])],
            ui.outputs[1:])
