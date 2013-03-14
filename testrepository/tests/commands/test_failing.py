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

import testtools
from testtools.compat import _b
from testtools.matchers import (
    DocTestMatches,
    Equals,
    )

from testrepository.commands import failing
from testrepository.ui.model import UI
from testrepository.repository import memory
from testrepository.tests import (
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
        class Cases(ResourcedTestCase):
            def failing(self):
                self.fail('foo')
            def ok(self):
                pass
        Cases('failing').run(inserter)
        Cases('ok').run(inserter)
        inserter.stopTestRun()
        self.assertEqual(1, cmd.execute())
        # We should have seen test outputs (of the failure) and summary data.
        self.assertEqual([
            ('results', Wildcard),
            ('summary', False, 1, None, Wildcard, None, [('id', 0, None), ('failures', 1, None)])],
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

    def test_with_subunit_shows_subunit_stream(self):
        ui, cmd = self.get_test_ui_and_cmd(options=[('subunit', True)])
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
        inserter.stopTestRun()
        self.assertEqual(0, cmd.execute())
        self.assertEqual(1, len(ui.outputs))
        self.assertEqual('stream', ui.outputs[0][0])
        self.assertThat(ui.outputs[0][1].decode('utf8'),
            DocTestMatches("""...test: ...failing
...failure: ...failing...""", doctest.ELLIPSIS))

    def test_with_subunit_no_failures_exit_0(self):
        ui, cmd = self.get_test_ui_and_cmd(options=[('subunit', True)])
        cmd.repository_factory = memory.RepositoryFactory()
        repo = cmd.repository_factory.initialise(ui.here)
        inserter = repo.get_inserter()
        inserter.startTestRun()
        class Cases(ResourcedTestCase):
            def ok(self):
                pass
        Cases('ok').run(inserter)
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
        class Cases(ResourcedTestCase):
            def failing1(self):
                self.fail('foo')
            def failing2(self):
                self.fail('bar')
            def ok(self):
                pass
        Cases('failing1').run(inserter)
        Cases('ok').run(inserter)
        Cases('failing2').run(inserter)
        inserter.stopTestRun()
        self.assertEqual(1, cmd.execute(), ui.outputs)
        self.assertEqual(1, len(ui.outputs))
        self.assertEqual('tests', ui.outputs[0][0])
        self.assertEqual(
            set([Cases('failing1').id(), Cases('failing2').id()]),
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
            class Cases(ResourcedTestCase):
                def failing(self):
                    self.fail('foo')
                def ok(self):
                    pass
            Cases('failing').run(inserter)
            Cases('ok').run(inserter)
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

    def test_grabs_TestCommand_result(self):
        ui, cmd = self.get_test_ui_and_cmd()
        cmd.repository_factory = memory.RepositoryFactory()
        calls = []
        cmd.repository_factory.initialise(ui.here)
        cmd.command_factory = StubTestCommand()
        cmd.execute()
        self.assertEqual(
            [('startTestRun',), ('stopTestRun',)],
            cmd.command_factory.results[0]._events)
