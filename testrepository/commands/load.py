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

from cStringIO import StringIO

import subunit.test_results
from testtools import MultiTestResult, TestResult

from testrepository.commands import Command

class load(Command):
    """Load a subunit stream into a repository.
    
    Failing tests are shown on the console and a summary of the stream is
    printed at the end.
    """

    input_streams = ['subunit+']

    def run(self):
        path = self.ui.here
        repo = self.repository_factory.open(path)
        failed = False
        for stream in self.ui.iter_streams('subunit'):
            inserter = repo.get_inserter()
            evaluator = TestResult()
            output = StringIO()
            output_stream = subunit.TestProtocolClient(output)
            filtered = subunit.test_results.TestResultFilter(output_stream,
                filter_skip=True)
            case = subunit.ProtocolTestCase(stream)
            inserter.startTestRun()
            try:
                case.run(MultiTestResult(inserter, evaluator, filtered))
            finally:
                run_id = inserter.stopTestRun()
            failed = failed or not evaluator.wasSuccessful()
            self.output_run(run_id, output, evaluator)
        if failed:
            return 1
        else:
            return 0
