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

from testrepository.commands import last
from testrepository.ui.model import UI
from testrepository.repository import memory
from testrepository.tests import (
    ResourcedTestCase,
    StubTestCommand,
    Wildcard,
    )


class TestCommand(ResourcedTestCase):

    def get_test_ui_and_cmd(self,args=()):
        ui = UI(args=args)
        cmd = last.last(ui)
        ui.set_command(cmd)
        return ui, cmd

    def test_shows_last_run(self):
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
            ('summary', False, 2, 0, Wildcard, 0.0,
             [('id', id, None), ('failures', 1, 0)])],
            ui.outputs)
        suite = ui.outputs[0][1]
        result = testtools.TestResult()
        result.startTestRun()
        try:
            suite.run(result)
        finally:
            result.stopTestRun()
        self.assertEqual(1, result.testsRun)
        self.assertEqual(1, len(result.failures))

    def test_grabs_TestCommand_result(self):
        ui, cmd = self.get_test_ui_and_cmd()
        cmd.repository_factory = memory.RepositoryFactory()
        repo = cmd.repository_factory.initialise(ui.here)
        inserter = repo.get_inserter()
        inserter.startTestRun()
        id = inserter.stopTestRun()
        cmd.command_factory = StubTestCommand
        StubTestCommand.results = []
        # None, None would be nice here, but sigh, default arguments etc.
        self.addCleanup(StubTestCommand.results.__delslice__, 0, 100)
        cmd.execute()
        self.assertEqual(
            [('startTestRun',), Wildcard, Wildcard, ('stopTestRun',)],
            StubTestCommand.results[0]._events)
