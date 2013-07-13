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

from functools import partial
from operator import methodcaller
import optparse
import threading

from extras import try_import
v2_avail = try_import('subunit.ByteStreamToStreamResult')

import subunit.test_results
import testtools

from testrepository.arguments.path import ExistingPathArgument
from testrepository.commands import Command
from testrepository.repository import RepositoryNotFound
from testrepository.testcommand import TestCommand

class InputToStreamResult(object):
    """Generate Stream events from stdin.

    Really a UI responsibility?
    """

    def __init__(self, stream):
        self.source = stream
        self.stop = False

    def run(self, result):
        while True:
            if self.stop:
                return
            char = self.source.read(1)
            if not char:
                return
            if char == b'a':
                result.status(test_id='stdin', test_status='fail')


class load(Command):
    """Load a subunit stream into a repository.

    Failing tests are shown on the console and a summary of the stream is
    printed at the end.

    Unless the stream is a partial stream, any existing failures are discarded.
    """

    input_streams = ['subunit+', 'interactive?']

    args = [ExistingPathArgument('streams', min=0, max=None)]
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
            help="No-op - deprecated and kept only for backwards compat."),
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
        # Not a full implementation of TestCase, but we only need to iterate
        # back to it. Needs to be a callable - its a head fake for
        # testsuite.add.
        # XXX: Be nice if we could declare that the argument, which is a path,
        # is to be an input stream - and thus push this conditional down into
        # the UI object.
        if self.ui.arguments.get('streams'):
            opener = partial(open, mode='rb')
            streams = map(opener, self.ui.arguments['streams'])
        else:
            streams = self.ui.iter_streams('subunit')
        def make_tests():
            for pos, stream in enumerate(streams):
                if v2_avail:
                    # Calls StreamResult API.
                    case = subunit.ByteStreamToStreamResult(
                        stream, non_subunit_name='stdout')
                else:
                    # Calls TestResult API.
                    case = subunit.ProtocolTestCase(stream)
                    def wrap_result(result):
                        # Wrap in a router to mask out startTestRun/stopTestRun from the
                        # ExtendedToStreamDecorator.
                        result = testtools.StreamResultRouter(
                            result, do_start_stop_run=False)
                        # Wrap that in ExtendedToStreamDecorator to convert v1 calls to
                        # StreamResult.
                        return testtools.ExtendedToStreamDecorator(result)
                    # Now calls StreamResult API :).
                    case = testtools.DecorateTestCaseResult(case, wrap_result,
                        methodcaller('startTestRun'),
                        methodcaller('stopTestRun'))
                case = testtools.DecorateTestCaseResult(case,
                    lambda result:testtools.StreamTagger(
                        [result], add=['worker-%d' % pos]))
                yield (case, str(pos))
        case = testtools.ConcurrentStreamTestSuite(make_tests)
        # One unmodified copy of the stream to repository storage
        inserter = repo.get_inserter(partial=self.ui.options.partial)
        # One copy of the stream to the UI layer after performing global
        # filters.
        try:
            previous_run = repo.get_latest_run()
        except KeyError:
            previous_run = None
        output_result, summary_result = self.ui.make_result(
            inserter.get_id, testcommand, previous_run=previous_run)
        result = testtools.CopyStreamResult([inserter, output_result])
        runner_thread = None
        result.startTestRun()
        try:
            # Convert user input into a stdin event stream
            interactive_streams = list(self.ui.iter_streams('interactive'))
            if interactive_streams:
                case = InputToStreamResult(interactive_streams[0])
                runner_thread = threading.Thread(
                    target=case.run, args=(result,))
                runner_thread.daemon = True
                runner_thread.start()
            case.run(result)
        finally:
            result.stopTestRun()
            if interactive_streams and runner_thread:
                runner_thread.stop = True
                runner_thread.join(10)
        if not summary_result.wasSuccessful():
            return 1
        else:
            return 0
