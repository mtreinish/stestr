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

"""Show the longest running tests in the repository."""

from operator import itemgetter

from testtools import TestResult

from testrepository.commands import Command


class TestIDCapturer(TestResult):
    """Capture the test ids from a test run.

    After using the result with a test run, the ids of
    the tests that were run are available in the ids
    attribute.
    """

    def __init__(self):
        super(TestIDCapturer, self).__init__()
        self.ids = []

    def startTest(self, test):
        super(TestIDCapturer, self).startTest(test)
        self.ids.append(test.id())


class slowest(Command):
    """Show the slowest tests from the last test run.

    This command shows a table, with the longest running
    tests at the top.
    """

    def run(self):
        repo = self.repository_factory.open(self.ui.here)
        try:
            latest_id = repo.latest_id()
        except KeyError:
            return 3
        run = repo.get_test_run(latest_id)
        # XXX: Push the get ids stuff down in to repo
        result = TestIDCapturer()
        run.get_test().run(result)
        test_times = repo.get_test_times(result.ids)
        known_times = test_times['known'].items()
        known_times.sort(key=itemgetter(1), reverse=True)
        rows = known_times
        self.ui.output_table(rows)
        return 0
