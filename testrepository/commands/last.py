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

"""Show the last run loaded into a repository."""

from testrepository.commands import Command
from testrepository.testcommand import TestCommand


class last(Command):
    """Show the last run loaded into a repository.

    Failing tests are shown on the console and a summary of the run is printed
    at the end.
    """

    # Can be assigned to to inject a custom command factory.
    command_factory = TestCommand

    def run(self):
        repo = self.repository_factory.open(self.ui.here)
        testcommand = self.command_factory(self.ui, repo)
        latest_run = repo.get_latest_run()
        case = latest_run.get_test()
        try:
            previous_run = repo.get_test_run(repo.latest_id() - 1)
        except KeyError:
            previous_run = None
        failed = False
        result = self.ui.make_result(
            latest_run.get_id, testcommand, previous_run=previous_run)
        result.startTestRun()
        try:
            case.run(result)
        finally:
            result.stopTestRun()
        failed = not result.wasSuccessful()
        if failed:
            return 1
        else:
            return 0
