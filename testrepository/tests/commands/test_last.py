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

"""Tests for the last command."""

import testtools
from testtools.matchers import Equals

from testrepository.commands import last
from testrepository.ui.model import UI
from testrepository.repository import memory
from testrepository.tests import (
    ResourcedTestCase,
    StubTestCommand,
    Wildcard,
    )


class TestCommand(ResourcedTestCase):

    def get_test_ui_and_cmd(self, args=(), options=()):
        ui = UI(args=args, options=options)
        cmd = last.last(ui)
        ui.set_command(cmd)
        return ui, cmd

    def test_shows_last_run_first_run(self):
        ui, cmd = self.get_test_ui_and_cmd()
        cmd.repository_factory = memory.RepositoryFactory()
        repo = cmd.repository_factory.initialise(ui.here)
        inserter = repo.get_inserter()
        inserter.startTestRun()
        class Cases(ResourcedTestCase):
            def failing(self):
                self.fail('foo')
            def ok(self):
                pass
        Cases('failing').run(inserter)
        Cases('ok').run(inserter)
        id = inserter.stopTestRun()
        self.assertEqual(1, cmd.execute())
        # We should have seen test outputs (of the failure) and summary data.
        self.assertEqual([
            ('results', Wildcard),
            ('summary', False, 2, None, Wildcard, Wildcard,
             [('id', id, None), ('failures', 1, None)])],
            ui.outputs)
        suite = ui.outputs[0][1]
        result = testtools.TestResult()
        result.startTestRun()
        try:
            suite.run(result)
        finally:
            result.stopTestRun()
        self.assertEqual(1, len(result.failures))
        self.assertEqual(2, result.testsRun)

    def _add_run(self, repo):
        inserter = repo.get_inserter()
        inserter.startTestRun()
        class Cases(ResourcedTestCase):
            def failing(self):
                self.fail('foo')
            def ok(self):
                pass
        Cases('failing').run(inserter)
        Cases('ok').run(inserter)
        return inserter.stopTestRun()

    def test_shows_last_run(self):
        ui, cmd = self.get_test_ui_and_cmd()
        cmd.repository_factory = memory.RepositoryFactory()
        repo = cmd.repository_factory.initialise(ui.here)
        self._add_run(repo)
        id = self._add_run(repo)
        self.assertEqual(1, cmd.execute())
        # We should have seen test outputs (of the failure) and summary data.
        self.assertEqual([
            ('results', Wildcard),
            ('summary', False, 2, 0, Wildcard, Wildcard,
             [('id', id, None), ('failures', 1, 0)])],
            ui.outputs)
        suite = ui.outputs[0][1]
        result = testtools.TestResult()
        result.startTestRun()
        try:
            suite.run(result)
        finally:
            result.stopTestRun()
        self.assertEqual(1, len(result.failures))
        self.assertEqual(2, result.testsRun)

    def test_grabs_TestCommand_result(self):
        ui, cmd = self.get_test_ui_and_cmd()
        cmd.repository_factory = memory.RepositoryFactory()
        repo = cmd.repository_factory.initialise(ui.here)
        inserter = repo.get_inserter()
        inserter.startTestRun()
        inserter.stopTestRun()
        cmd.command_factory = StubTestCommand()
        cmd.execute()
        self.assertEqual(
            [('startTestRun',), ('stopTestRun',)],
            cmd.command_factory.results[0]._events)

    def test_shows_subunit_stream(self):
        ui, cmd = self.get_test_ui_and_cmd(options=[('subunit', True)])
        cmd.repository_factory = memory.RepositoryFactory()
        repo = cmd.repository_factory.initialise(ui.here)
        self._add_run(repo)
        self.assertEqual(0, cmd.execute())
        # We should have seen test outputs (of the failure) and summary data.
        self.assertEqual([
            ('stream', Wildcard),
            ], ui.outputs)
        self.assertThat(ui.outputs[0][1], Equals("""\
test: testrepository.tests.commands.test_last.Cases.failing
failure: testrepository.tests.commands.test_last.Cases.failing [ multipart
Content-Type: text/x-traceback;charset=utf8,language=python
traceback
95\r
Traceback (most recent call last):
  File "testrepository/tests/commands/test_last.py", line 74, in failing
    self.fail('foo')
AssertionError: foo
0\r
]
test: testrepository.tests.commands.test_last.Cases.ok
successful: testrepository.tests.commands.test_last.Cases.ok [ multipart
]
"""))
