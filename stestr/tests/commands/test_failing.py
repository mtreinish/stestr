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

"""Tests for the failing command."""

import doctest
from io import BytesIO

from subunit.v2 import ByteStreamToStreamResult
import testtools
from testtools.compat import _b
from testtools.matchers import (
    DocTestMatches,
    Equals,
    )
from testtools.testresult.doubles import StreamResult

from stestr.commands import failing
from stestr.ui.model import UI
from stestr.repository import memory
from stestr.tests import (
    ResourcedTestCase,
    StubTestCommand,
    Wildcard,
    )


class TestCommand(ResourcedTestCase):

    def get_test_ui_and_cmd(self, options=(), args=()):
        ui = UI(options=options, args=args)
        cmd = failing.failing(ui)
        ui.set_command(cmd)
        return ui, cmd

    def test_shows_failures_from_last_run(self):
        ui, cmd = self.get_test_ui_and_cmd()
        cmd.repository_factory = memory.RepositoryFactory()
        repo = cmd.repository_factory.initialise(ui.here)
        inserter = repo.get_inserter()
        inserter.startTestRun()
        inserter.status(test_id='failing', test_status='fail')
        inserter.status(test_id='ok', test_status='success')
        inserter.stopTestRun()
        self.assertEqual(1, cmd.execute())
        # We should have seen test outputs (of the failure) and summary data.
        self.assertEqual([
            ('results', Wildcard),
            ('summary', False, 1, None, Wildcard, None, [('id', 0, None), ('failures', 1, None)])],
            ui.outputs)
        suite = ui.outputs[0][1]
        result = testtools.StreamSummary()
        result.startTestRun()
        try:
            suite.run(result)
        finally:
            result.stopTestRun()
        self.assertEqual(1, result.testsRun)
        self.assertEqual(1, len(result.errors))

    def test_with_subunit_shows_subunit_stream(self):
        ui, cmd = self.get_test_ui_and_cmd(options=[('subunit', True)])
        cmd.repository_factory = memory.RepositoryFactory()
        repo = cmd.repository_factory.initialise(ui.here)
        inserter = repo.get_inserter()
        inserter.startTestRun()
        inserter.status(test_id='failing', test_status='fail')
        inserter.status(test_id='ok', test_status='success')
        inserter.stopTestRun()
        self.assertEqual(0, cmd.execute())
        self.assertEqual(1, len(ui.outputs))
        self.assertEqual('stream', ui.outputs[0][0])
        as_subunit = BytesIO(ui.outputs[0][1])
        stream = ByteStreamToStreamResult(as_subunit)
        log = StreamResult()
        log.startTestRun()
        try:
            stream.run(log)
        finally:
            log.stopTestRun()
        self.assertEqual(
            log._events, [
            ('startTestRun',),
            ('status', 'failing', 'inprogress', None, True, None, None, False,
             None, None, Wildcard),
            ('status', 'failing', 'fail', None, True, None, None, False, None,
             None, Wildcard),
            ('stopTestRun',)
            ])

    def test_with_subunit_no_failures_exit_0(self):
        ui, cmd = self.get_test_ui_and_cmd(options=[('subunit', True)])
        cmd.repository_factory = memory.RepositoryFactory()
        repo = cmd.repository_factory.initialise(ui.here)
        inserter = repo.get_inserter()
        inserter.startTestRun()
        inserter.status(test_id='ok', test_status='success')
        inserter.stopTestRun()
        self.assertEqual(0, cmd.execute())
        self.assertEqual(1, len(ui.outputs))
        self.assertEqual('stream', ui.outputs[0][0])
        self.assertThat(ui.outputs[0][1], Equals(_b('')))

    def test_with_list_shows_list_of_tests(self):
        ui, cmd = self.get_test_ui_and_cmd(options=[('list', True)])
        cmd.repository_factory = memory.RepositoryFactory()
        repo = cmd.repository_factory.initialise(ui.here)
        inserter = repo.get_inserter()
        inserter.startTestRun()
        inserter.status(test_id='failing1', test_status='fail')
        inserter.status(test_id='ok', test_status='success')
        inserter.status(test_id='failing2', test_status='fail')
        inserter.stopTestRun()
        self.assertEqual(1, cmd.execute(), ui.outputs)
        self.assertEqual(1, len(ui.outputs))
        self.assertEqual('tests', ui.outputs[0][0])
        self.assertEqual(
            set(['failing1', 'failing2']),
            set([test.id() for test in ui.outputs[0][1]]))

    def test_uses_get_failing(self):
        ui, cmd = self.get_test_ui_and_cmd()
        cmd.repository_factory = memory.RepositoryFactory()
        calls = []
        open = cmd.repository_factory.open
        def decorate_open_with_get_failing(url):
            repo = open(url)
            inserter = repo.get_inserter()
            inserter.startTestRun()
            inserter.status(test_id='failing', test_status='fail')
            inserter.status(test_id='ok', test_status='success')
            inserter.stopTestRun()
            orig = repo.get_failing
            def get_failing():
                calls.append(True)
                return orig()
            repo.get_failing = get_failing
            return repo
        cmd.repository_factory.open = decorate_open_with_get_failing
        cmd.repository_factory.initialise(ui.here)
        self.assertEqual(1, cmd.execute())
        self.assertEqual([True], calls)
