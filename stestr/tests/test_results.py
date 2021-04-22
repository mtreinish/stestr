# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import datetime
from datetime import datetime as dt
import sys

from stestr import results
from stestr.tests import base


class TestSummarizingResult(base.TestCase):
    def setUp(self):
        super(TestSummarizingResult, self).setUp()
        self.sr = results.SummarizingResult()
        self.sr.startTestRun()

    def test_status(self):
        # just call status with no arguments
        self.sr.status()
        self.assertEqual(None, self.sr._last_time)
        # set status
        ts = dt.now()
        self.sr.status(timestamp=ts)
        self.assertEqual(ts, self.sr._last_time)
        # update status by past time
        ts = ts - datetime.timedelta(seconds=3600)
        self.sr.status(timestamp=ts)
        self.assertEqual(ts, self.sr._first_time)
        # update status
        ts = dt.now()
        self.sr.status(timestamp=ts)
        self.assertEqual(ts, self.sr._last_time)

    def test_get_num_failures_zero(self):
        self.assertEqual(0, self.sr.get_num_failures())

    def test_get_num_failures_three(self):
        self.sr.failures = [1, 2]
        self.sr.errors = [3]
        self.assertEqual(3, self.sr.get_num_failures())

    def test_get_time_taken_none(self):
        self.assertEqual(None, self.sr.get_time_taken())

    def test_get_time_taken_three(self):
        now = dt.now()
        self.sr._first_time = now
        self.sr._last_time = now + datetime.timedelta(seconds=3)
        self.assertEqual(3, self.sr.get_time_taken())


class TestCatFiles(base.TestCase):
    def setUp(self):
        super(TestCatFiles, self).setUp()
        self.cat_files = results.CatFiles(sys.stdout)

    def test_status_file_name_none(self):
        self.cat_files.status(file_name=None)
        self.assertEqual(None, self.cat_files.last_file)

    def test_status_file_name_foo(self):
        self.cat_files.status(file_name='foo', file_bytes=b'abc')
        self.assertEqual('foo', self.cat_files.last_file)
        # Try again with the same file name
        self.cat_files.status(file_name='foo', file_bytes=b'abc')
        self.assertEqual('foo', self.cat_files.last_file)
