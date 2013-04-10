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

from datetime import (
    datetime,
    timedelta,
    )
import sys
from threading import Semaphore

from testtools import (
    TestCase,
    TestResult,
    ThreadsafeForwardingResult,
    )

from testrepository.results import (
    SummarizingResult,
    )
from testrepository.ui import BaseUITestResult
from testrepository.ui.model import UI


class TestSummarizingResult(TestCase):

    def test_empty(self):
        result = SummarizingResult()
        result.startTestRun()
        result.stopTestRun()
        self.assertEqual(0, result.testsRun)
        self.assertEqual(0, result.get_num_failures())
        self.assertIs(None, result.get_time_taken())

    def test_time_taken(self):
        result = SummarizingResult()
        now = datetime.now()
        result.startTestRun()
        result.status(timestamp=now)
        result.status(timestamp=now + timedelta(seconds=5))
        result.stopTestRun()
        self.assertEqual(5.0, result.get_time_taken())

    def test_num_failures(self):
        result = SummarizingResult()
        result.startTestRun()
        try:
            1/0
        except ZeroDivisionError:
            error = sys.exc_info()
        result.status(test_id='foo', test_status='fail')
        result.status(test_id='foo', test_status='fail')
        result.stopTestRun()
        self.assertEqual(2, result.get_num_failures())

    def test_tests_run(self):
        result = SummarizingResult()
        result.startTestRun()
        for i in range(5):
            result.status(test_id='foo', test_status='success')
        result.stopTestRun()
        self.assertEqual(5, result.testsRun)
