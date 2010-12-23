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

import testtools

from testrepository.commands import load
from testrepository.ui.model import UI
from testrepository.tests import ResourcedTestCase, Wildcard
from testrepository.tests.test_repository import RecordingRepositoryFactory
from testrepository.repository import memory


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
            [('values', [('id', 0), ('tests', 1), ('failures', 1)])],
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
            ('values', [('id', 0), ('tests', 1), ('failures', 1)])],
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
             ('values', [('id', 0), ('tests', 1), ('skips', 1)])],
            ui.outputs)

    def test_load_new_shows_test_summary_no_tests(self):
        ui = UI([('subunit', '')])
        cmd = load.load(ui)
        ui.set_command(cmd)
        cmd.repository_factory = memory.RepositoryFactory()
        cmd.repository_factory.initialise(ui.here)
        self.assertEqual(0, cmd.execute())
        self.assertEqual(
            [('results', Wildcard), ('values', [('id', 0), ('tests', 0)])],
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
