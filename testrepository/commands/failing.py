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

"""Show the current failures in the repository."""

from cStringIO import StringIO
import optparse

import subunit.test_results
from testtools import MultiTestResult, TestResult

from testrepository.commands import Command

class failing(Command):
    """Show the current failures known by the repository.
    
    Today this is the failures from the most recent run, but once partial
    and full runs are understood it will be all the failures from the last
    full run combined with any failures in subsequent partial runs, minus any
    passes that have occured in a run more recent than a given failure. Deleted
    tests will only be detected on full runs with this approach.
    """

    options = [
        optparse.Option(
            "--subunit", action="store_true",
            default=False, help="Show output as a subunit stream."),
        optparse.Option(
            "--list", action="store_true",
            default=False, help="Show only a list of failing tests."),
        ]

    def _list_subunit(self, run):
        # TODO only failing tests.
        stream = run.get_subunit_stream()
        self.ui.output_stream(stream)
        if stream:
            return 1
        else:
            return 0

    def _make_result(self, evaluator):
        if self.ui.options.list:
            return evaluator
        output_result = self.ui.make_result()
        filtered = subunit.test_results.TestResultFilter(
            output_result, filter_skip=True)
        return MultiTestResult(evaluator, filtered)

    def run(self):
        repo = self.repository_factory.open(self.ui.here)
        run = repo.get_failing()
        if self.ui.options.subunit:
            return self._list_subunit(run)
        case = run.get_test()
        failed = False
        evaluator = TestResult()
        result = self._make_result(evaluator)
        result.startTestRun()
        try:
            case.run(result)
        finally:
            result.stopTestRun()
        failed = not evaluator.wasSuccessful()
        if failed:
            result = 1
        else:
            result = 0
        if self.ui.options.list:
            failing_tests = [
                test for test, _ in evaluator.errors + evaluator.failures]
            self.ui.output_tests(failing_tests)
            return result
        if self.ui.options.quiet:
            return result
        values = []
        failures = len(evaluator.failures) + len(evaluator.errors)
        if failures:
            values.append(('failures', failures))
        self.ui.output_values(values)
        return result
