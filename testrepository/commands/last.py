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

from cStringIO import StringIO

import subunit.test_results
from testtools import MultiTestResult, TestResult

from testrepository.commands import Command

class last(Command):
    """Show the last run loaded into a repository.

    Failing tests are shown on the console and a summary of the run is printed
    at the end.
    """

    def run(self):
        repo = self.repository_factory.open(self.ui.here)
        run_id = repo.latest_id()
        case = repo.get_test_run(run_id).get_test()
        failed = False
        evaluator = TestResult()
        output_result = self.ui.make_result()
        filtered = subunit.test_results.TestResultFilter(
            output_result, filter_skip=True)
        result = MultiTestResult(evaluator, filtered)
        result.startTestRun()
        try:
            case.run(result)
        finally:
            result.stopTestRun()
        failed = not evaluator.wasSuccessful()
        self.output_run(run_id, StringIO(), evaluator)
        if failed:
            return 1
        else:
            return 0
