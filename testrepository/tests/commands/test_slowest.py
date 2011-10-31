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

"""Tests for the "slowest" command."""

from datetime import (
    datetime,
    timedelta,
)
import pytz

from testtools import PlaceHolder

from testrepository.commands import slowest
from testrepository.ui.model import UI
from testrepository.repository import memory
from testrepository.tests import ResourcedTestCase


class TestCommand(ResourcedTestCase):

    def get_test_ui_and_cmd(self, options=(), args=()):
        ui = UI(options=options, args=args)
        cmd = slowest.slowest(ui)
        ui.set_command(cmd)
        return ui, cmd

    def test_shows_nothing_for_no_tests(self):
        """Having no tests leads to an error and no output."""
        ui, cmd = self.get_test_ui_and_cmd()
        cmd.repository_factory = memory.RepositoryFactory()
        repo = cmd.repository_factory.initialise(ui.here)
        self.assertEqual(3, cmd.execute())
        self.assertEqual([], ui.outputs)

    def insert_one_test_with_runtime(self, inserter, runtime):
        """Insert one test, with the specified run time.

        :param inserter: the inserter to use to insert the
            test.
        :param runtime: the runtime (in seconds) that the
            test should appear to take.
        :return: the name of the test that was added.
        """
        test_id = self.getUniqueString()
        start_time = datetime.now(pytz.UTC)
        inserter.time(start_time)
        test_case = PlaceHolder(test_id)
        inserter.startTest(test_case)
        inserter.time(
            start_time + timedelta(seconds=runtime))
        inserter.addSuccess(test_case)
        inserter.stopTest(test_case)
        return test_id

    def test_shows_one_test_when_one_test(self):
        """When there is one test it is shown."""
        ui, cmd = self.get_test_ui_and_cmd()
        cmd.repository_factory = memory.RepositoryFactory()
        repo = cmd.repository_factory.initialise(ui.here)
        inserter = repo.get_inserter()
        inserter.startTestRun()
        runtime = 0.1
        test_id = self.insert_one_test_with_runtime(
            inserter, runtime)
        inserter.stopTestRun()
        retcode = cmd.execute()
        self.assertEqual(0, retcode)
        self.assertEqual(
            [('table',
                [slowest.slowest.TABLE_HEADER,
                 (test_id, runtime)])],
            ui.outputs)

    def test_orders_tests_based_on_runtime(self):
        """Longer running tests are shown first."""
        ui, cmd = self.get_test_ui_and_cmd()
        cmd.repository_factory = memory.RepositoryFactory()
        repo = cmd.repository_factory.initialise(ui.here)
        inserter = repo.get_inserter()
        inserter.startTestRun()
        runtime1 = 1.1
        test_id1 = self.insert_one_test_with_runtime(
            inserter, runtime1)
        runtime2 = 0.1
        test_id2 = self.insert_one_test_with_runtime(
            inserter, runtime2)
        inserter.stopTestRun()
        retcode = cmd.execute()
        self.assertEqual(0, retcode)
        self.assertEqual(
            [('table',
                [slowest.slowest.TABLE_HEADER,
                 (test_id1, runtime1),
                 (test_id2, runtime2)])],
            ui.outputs)
