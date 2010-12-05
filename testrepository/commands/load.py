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

import subunit
from testtools import ConcurrentTestSuite, MultiTestResult

from testrepository.commands import Command
from testrepository.results import TestResultFilter


class load(Command):
    """Load a subunit stream into a repository.

    Failing tests are shown on the console and a summary of the stream is
    printed at the end.
    """

    input_streams = ['subunit+']

    def run(self):
        path = self.ui.here
        repo = self.repository_factory.open(path)
        run_id = None
        # Not a full implementation of TestCase, but we only need to iterate
        # back to it. Needs to be a callable - its a head fake for
        # testsuite.add.
        cases = lambda:self.ui.iter_streams('subunit')
        def make_tests(suite):
            streams = list(suite)[0]
            for stream in streams():
                yield subunit.ProtocolTestCase(stream)
        case = ConcurrentTestSuite(cases, make_tests)
        inserter = repo.get_inserter()
        output_result = self.ui.make_result(lambda: run_id)
        # XXX: We want to *count* skips, but not show them.
        filtered = TestResultFilter(output_result, filter_skip=False)
        filtered.startTestRun()
        inserter.startTestRun()
        try:
            case.run(MultiTestResult(inserter, filtered))
        finally:
            run_id = inserter.stopTestRun()
            filtered.stopTestRun()
        if not filtered.wasSuccessful():
            return 1
        else:
            return 0
