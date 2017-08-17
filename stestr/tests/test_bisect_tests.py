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

import io
import operator

import mock
import six
import subunit
import testtools

from stestr import bisect_tests
from stestr.repository import abstract
from stestr.tests import base


class FakeTestRun(abstract.AbstractTestRun):
    def get_test(self):
        case = subunit.ByteStreamToStreamResult(io.BytesIO(self._content))

        def wrap_result(result):
            # Wrap in a router to mask out startTestRun/stopTestRun from the
            # ExtendedToStreamDecorator.
            result = testtools.StreamResultRouter(
                result, do_start_stop_run=False)
            # Wrap that in ExtendedToStreamDecorator to convert v1 calls to
            # StreamResult.
            return testtools.ExtendedToStreamDecorator(result)

        return testtools.DecorateTestCaseResult(
            case, wrap_result, operator.methodcaller('startTestRun'),
            operator.methodcaller('stopTestRun'))

    def get_id(self):
        return self.id


class FakeFailedTestRunNoTags(FakeTestRun):

    def __init__(self, failure=True):
        # Generate a subunit stream
        self.id = 2
        stream_buf = io.BytesIO()
        stream = subunit.StreamResultToBytes(stream_buf)
        stream.status(test_id='test_a', test_status='inprogress')
        stream.status(test_id='test_a', test_status='success')
        stream.status(test_id='test_b', test_status='inprogress')
        stream.status(test_id='test_b', test_status='success')
        stream.status(test_id='test_c', test_status='inprogress')
        stream.status(test_id='test_c', test_status='fail')
        stream_buf.seek(0)
        self._content = stream_buf.getvalue()


class FakeFailingWithTags(FakeTestRun):

    def __init__(self, failure=True):
        # Generate a subunit stream
        self.id = None
        stream_buf = io.BytesIO()
        stream = subunit.StreamResultToBytes(stream_buf)
        stream.status(test_id='test_c', test_status='inprogress',
                      test_tags=['worker-0'])
        stream.status(test_id='test_c', test_status='fail',
                      test_tags=['worker-0'])
        stream_buf.seek(0)
        self._content = stream_buf.getvalue()


class FakeNoFailing(FakeTestRun):

    def __init__(self, failure=True):
        # Generate a subunit stream
        stream_buf = io.BytesIO(six.binary_type(''.encode('utf-8')))
        self._content = stream_buf.getvalue()
        self.id = None


class FakeFailedTestRunWithTags(FakeTestRun):

    def __init__(self, failure=True):
        # Generate a subunit stream
        stream_buf = io.BytesIO()
        stream = subunit.StreamResultToBytes(stream_buf)
        stream.status(test_id='test_a', test_status='inprogress',
                      test_tags=['worker-0'])
        stream.status(test_id='test_a', test_status='success',
                      test_tags=['worker-0'])
        stream.status(test_id='test_b', test_status='inprogress',
                      test_tags=['worker-1'])
        stream.status(test_id='test_b', test_status='success',
                      test_tags=['worker-1'])
        stream.status(test_id='test_c', test_status='inprogress',
                      test_tags=['worker-0'])
        stream.status(test_id='test_c', test_status='fail',
                      test_tags=['worker-0'])
        stream_buf.seek(0)
        self._content = stream_buf.getvalue()
        self.id = 2


class FakeFailedMultiWorkerTestRunWithTags(FakeTestRun):

    def __init__(self, failure=True):
        # Generate a subunit stream
        stream_buf = io.BytesIO()
        stream = subunit.StreamResultToBytes(stream_buf)
        stream.status(test_id='test_a', test_status='inprogress',
                      test_tags=['worker-0'])
        stream.status(test_id='test_a', test_status='success',
                      test_tags=['worker-0'])
        stream.status(test_id='test_b', test_status='inprogress',
                      test_tags=['worker-1'])
        stream.status(test_id='test_b', test_status='fail',
                      test_tags=['worker-1'])
        stream.status(test_id='test_c', test_status='inprogress',
                      test_tags=['worker-0'])
        stream.status(test_id='test_c', test_status='fail',
                      test_tags=['worker-0'])
        stream_buf.seek(0)
        self._content = stream_buf.getvalue()
        self.id = 2


class TestBisectTests(base.TestCase):
    def setUp(self):
        super(TestBisectTests, self).setUp()
        self.repo_mock = mock.create_autospec(
            'stestr.repository.file.Repository')
        self.conf_mock = mock.create_autospec('stestr.config_file.TestrConf')
        self.run_func_mock = mock.MagicMock()
        self.latest_run_mock = mock.MagicMock()

    def test_bisect_no_failures_provided(self):
        bisector = bisect_tests.IsolationAnalyzer(
            self.latest_run_mock, self.conf_mock, self.run_func_mock,
            self.repo_mock)
        self.assertRaises(ValueError, bisector.bisect_tests, [])

    def test_prior_tests_invlaid_test_id(self):
        bisector = bisect_tests.IsolationAnalyzer(
            self.latest_run_mock, self.conf_mock, self.run_func_mock,
            self.repo_mock)
        run = FakeFailedTestRunNoTags()
        self.assertRaises(KeyError, bisector._prior_tests, run, 'bad_test_id')

    def test_get_prior_tests_no_tags(self):
        bisector = bisect_tests.IsolationAnalyzer(
            self.latest_run_mock, self.conf_mock, self.run_func_mock,
            self.repo_mock)
        run = FakeFailedTestRunNoTags()
        prior_tests = bisector._prior_tests(run, 'test_c')
        self.assertEqual(['test_a', 'test_b'], prior_tests)

    def test_get_prior_tests_with_tags(self):
        bisector = bisect_tests.IsolationAnalyzer(
            self.latest_run_mock, self.conf_mock, self.run_func_mock,
            self.repo_mock)
        run = FakeFailedTestRunWithTags()
        prior_tests = bisector._prior_tests(run, 'test_c')
        self.assertEqual(['test_a'], prior_tests)

    @mock.patch('stestr.output.output_table')
    def test_bisect_tests_isolated_failure(self, table_mock):
        run = FakeFailedTestRunWithTags()
        self.conf_mock.get_run_command = mock.MagicMock()

        def get_failures(*args, **kwargs):
            return FakeNoFailing()

        self.repo_mock.get_failing = get_failures
        bisector = bisect_tests.IsolationAnalyzer(
            run, self.conf_mock, self.run_func_mock, self.repo_mock)
        return_code = bisector.bisect_tests(['test_c'])
        expected_issue = [('failing test', 'caused by test'),
                          ('test_c', 'unknown - no conflicts')]
        table_mock.assert_called_once_with(expected_issue)
        self.assertEqual(3, return_code)

    @mock.patch('stestr.output.output_table')
    def test_bisect_tests_not_isolated_failure(self, table_mock):
        run = FakeFailedTestRunWithTags()
        self.conf_mock.get_run_command = mock.MagicMock()

        def get_failures(*args, **kwargs):
            return FakeFailingWithTags()

        self.repo_mock.get_failing = get_failures
        bisector = bisect_tests.IsolationAnalyzer(
            run, self.conf_mock, self.run_func_mock, self.repo_mock)
        return_code = bisector.bisect_tests(['test_c'])
        expected_issue = [('failing test', 'caused by test'),
                          ('test_c', 'test_a')]
        table_mock.assert_called_once_with(expected_issue)
        self.assertEqual(3, return_code)

    @mock.patch('stestr.output.output_table')
    def test_bisect_tests_not_isolated_multiworker_failures(self, table_mock):
        run = FakeFailedMultiWorkerTestRunWithTags()
        self.conf_mock.get_run_command = mock.MagicMock()

        def get_failures(*args, **kwargs):
            return FakeFailingWithTags()

        self.repo_mock.get_failing = get_failures
        bisector = bisect_tests.IsolationAnalyzer(
            run, self.conf_mock, self.run_func_mock, self.repo_mock)
        return_code = bisector.bisect_tests(['test_b', 'test_c'])
        expected_issue = [('failing test', 'caused by test'),
                          ('test_b', 'unknown - no conflicts'),
                          ('test_c', 'test_a')]
        table_mock.assert_called_once_with(expected_issue)
        self.assertEqual(3, return_code)
