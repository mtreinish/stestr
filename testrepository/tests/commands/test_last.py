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
from testtools.compat import _b
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
        inserter.status(test_id='failing', test_status='fail')
        inserter.status(test_id='ok', test_status='success')
        inserter.stopTestRun()
        id = inserter.get_id()
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
        inserter.status(test_id='failing', test_status='fail')
        inserter.status(test_id='ok', test_status='success')
        inserter.stopTestRun()
        return inserter.get_id()

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
        self.assertThat(ui.outputs[0][1], Equals(_b("""\
test: failing
failure: failing [ multipart
]
test: ok
successful: ok [ multipart
]
""")))
