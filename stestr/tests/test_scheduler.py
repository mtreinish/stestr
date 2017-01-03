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
import re

from subunit import iso8601

from stestr.repository import memory
from stestr import scheduler
from stestr.tests import base


class TestScheduler(base.TestCase):

    def _add_timed_test(self, id, duration, result, enumeration=False):
        start = datetime.datetime.now()
        start = start.replace(tzinfo=iso8601.UTC)
        if enumeration:
            result.status(test_id=id, test_status='exists', timestamp=start)
        else:
            result.status(test_id=id, test_status='inprogress',
                          timestamp=start)
            timestamp = start + datetime.timedelta(seconds=duration)
            result.status(test_id=id, test_status='success',
                          timestamp=timestamp)

    def test_partition_tests(self):
        repo = memory.RepositoryFactory().initialise('memory:')
        result = repo.get_inserter()
        result.startTestRun()
        self._add_timed_test("slow", 3, result)
        self._add_timed_test("fast1", 1, result)
        self._add_timed_test("fast2", 1, result)
        result.stopTestRun()
        test_ids = frozenset(['slow', 'fast1', 'fast2', 'unknown1',
                              'unknown2', 'unknown3', 'unknown4'])
        partitions = scheduler.partition_tests(test_ids, 2, repo, None)
        self.assertTrue('slow' in partitions[0])
        self.assertFalse('fast1' in partitions[0])
        self.assertFalse('fast2' in partitions[0])
        self.assertFalse('slow' in partitions[1])
        self.assertTrue('fast1' in partitions[1])
        self.assertTrue('fast2' in partitions[1])
        self.assertEqual(3, len(partitions[0]))
        self.assertEqual(4, len(partitions[1]))

    def test_partition_tests_with_zero_duration(self):
        repo = memory.RepositoryFactory().initialise('memory:')
        result = repo.get_inserter()
        result.startTestRun()
        self._add_timed_test("zero1", 0, result)
        self._add_timed_test("zero2", 0, result)
        result.stopTestRun()
        # Partitioning by two should generate two one-entry partitions.
        test_ids = frozenset(['zero1', 'zero2'])
        partitions = scheduler.partition_tests(test_ids, 2, repo, None)
        self.assertEqual(1, len(partitions[0]))
        self.assertEqual(1, len(partitions[1]))

    def test_partition_tests_with_grouping(self):
        repo = memory.RepositoryFactory().initialise('memory:')
        result = repo.get_inserter()
        result.startTestRun()
        self._add_timed_test("TestCase1.slow", 3, result)
        self._add_timed_test("TestCase2.fast1", 1, result)
        self._add_timed_test("TestCase2.fast2", 1, result)
        result.stopTestRun()
        test_ids = frozenset(['TestCase1.slow', 'TestCase1.fast',
                              'TestCase1.fast2', 'TestCase2.fast1',
                              'TestCase3.test1', 'TestCase3.test2',
                              'TestCase2.fast2', 'TestCase4.test',
                              'testdir.testfile.TestCase5.test'])

        def group_id(test_id, regex=re.compile('TestCase[0-5]')):
            match = regex.match(test_id)
            if match:
                return match.group(0)

        partitions = scheduler.partition_tests(test_ids, 2, repo, group_id)
        # Timed groups are deterministic:
        self.assertTrue('TestCase2.fast1' in partitions[0])
        self.assertTrue('TestCase2.fast2' in partitions[0])
        self.assertTrue('TestCase1.slow' in partitions[1])
        self.assertTrue('TestCase1.fast' in partitions[1])
        self.assertTrue('TestCase1.fast2' in partitions[1])
        # Untimed groups just need to be kept together:
        if 'TestCase3.test1' in partitions[0]:
            self.assertTrue('TestCase3.test2' in partitions[0])
        if 'TestCase4.test' not in partitions[0]:
            self.assertTrue('TestCase4.test' in partitions[1])
        if 'testdir.testfile.TestCase5.test' not in partitions[0]:
            self.assertTrue('testdir.testfile.TestCase5.test' in partitions[1])
