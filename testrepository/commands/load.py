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

"""Load data into a repository."""

import optparse

import subunit
from testtools import ConcurrentTestSuite, MultiTestResult, Tagger

from testrepository.commands import Command
from testrepository.repository import RepositoryNotFound
from testrepository.testcommand import TestCommand


def _wrap_result(result, thread_number):
    worker_id = 'worker-%s' % thread_number
    tags_to_add = set([worker_id])
    tags_to_remove = set()
    return Tagger(result, tags_to_add, tags_to_remove)


class load(Command):
    """Load a subunit stream into a repository.

    Failing tests are shown on the console and a summary of the stream is
    printed at the end.

    Unless the stream is a partial stream, any existing failures are discarded.
    """

    input_streams = ['subunit+']

    options = [
        optparse.Option("--partial", action="store_true",
            default=False, help="The stream being loaded was a partial run."),
        optparse.Option(
            "--force-init", action="store_true",
            default=False,
            help="Initialise the repository if it does not exist already"),
        optparse.Option("--subunit", action="store_true",
            default=False, help="Display results in subunit format."),
        optparse.Option("--full-results", action="store_true",
            default=False,
            help="Show all test results. Currently only works with --subunit."),
        ]
    # Can be assigned to to inject a custom command factory.
    command_factory = TestCommand

    def run(self):
        path = self.ui.here
        try:
            repo = self.repository_factory.open(path)
        except RepositoryNotFound:
            if self.ui.options.force_init:
                repo = self.repository_factory.initialise(path)
            else:
                raise
        testcommand = self.command_factory(self.ui, repo)
        run_id = None
        # Not a full implementation of TestCase, but we only need to iterate
        # back to it. Needs to be a callable - its a head fake for
        # testsuite.add.
        cases = lambda:self.ui.iter_streams('subunit')
        def make_tests(suite):
            streams = list(suite)[0]
            for stream in streams():
                yield subunit.ProtocolTestCase(stream)
        case = ConcurrentTestSuite(cases, make_tests, _wrap_result)
        # One copy of the stream to repository storage
        inserter = repo.get_inserter(partial=self.ui.options.partial)
        # One copy of the stream to the UI layer after performing global
        # filters.
        try:
            previous_run = repo.get_latest_run()
        except KeyError:
            previous_run = None
        output_result = self.ui.make_result(
            lambda: run_id, testcommand, previous_run=previous_run)
        result = MultiTestResult(inserter, output_result)
        result.startTestRun()
        try:
            case.run(result)
        finally:
            # Does not call result.stopTestRun because the lambda: run_id above
            # needs the local variable to be updated before the
            # filtered.stopTestRun() call is invoked. This could be fixed by
            # having a capturing result rather than a lambda, but thats more
            # code.
            run_id = inserter.stopTestRun()
            output_result.stopTestRun()
        if not output_result.wasSuccessful():
            return 1
        else:
            return 0
