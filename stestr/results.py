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

import six
import subunit
import testtools

from stestr import output


def wasSuccessful(summary):
    return not (summary.errors or summary.failures or
                summary.unexpectedSuccesses)


class SummarizingResult(testtools.StreamSummary):

    def __init__(self):
        super(SummarizingResult, self).__init__()

    def startTestRun(self):
        super(SummarizingResult, self).startTestRun()
        self._first_time = None
        self._last_time = None

    def status(self, *args, **kwargs):
        if kwargs.get('timestamp') is not None:
            timestamp = kwargs['timestamp']
            if self._last_time is None:
                self._first_time = timestamp
                self._last_time = timestamp
            if timestamp < self._first_time:
                self._first_time = timestamp
            if timestamp > self._last_time:
                self._last_time = timestamp
        super(SummarizingResult, self).status(*args, **kwargs)

    def get_num_failures(self):
        return len(self.failures) + len(self.errors)

    def get_time_taken(self):
        if None in (self._last_time, self._first_time):
            return None
        return (self._last_time - self._first_time).total_seconds()


class CatFiles(testtools.StreamResult):
    """Cat file attachments received to a stream."""

    def __init__(self, byte_stream):
        self.stream = subunit.make_stream_binary(byte_stream)
        self.last_file = None

    def status(self, test_id=None, test_status=None, test_tags=None,
               runnable=True, file_name=None, file_bytes=None, eof=False,
               mime_type=None, route_code=None, timestamp=None):
        if file_name is None:
            return
        if self.last_file != file_name:
            self.stream.write(("--- %s ---\n" % file_name).encode('utf8'))
            self.last_file = file_name
        self.stream.write(file_bytes)
        self.stream.flush()


class CLITestResult(testtools.StreamResult):
    """A TestResult for the CLI."""

    def __init__(self, get_id, stream, previous_run=None):
        """Construct a CLITestResult writing to stream.

        :param get_id: A nullary callable that returns the id of the test run.
                       This expects a callable instead of the actual value
                       because in some repository backends the run_id is only
                       generated after stopTestRun() is called.
        :param stream: The stream to use for result
        :param previous_run: The CLITestResult for the previous run
        """
        super(CLITestResult, self).__init__()
        self._previous_run = previous_run
        self._summary = SummarizingResult()
        self.stream = testtools.compat.unicode_output_stream(stream)
        self.sep1 = testtools.compat._u('=' * 70 + '\n')
        self.sep2 = testtools.compat._u('-' * 70 + '\n')
        self.filterable_states = set(['success', 'uxsuccess', 'xfail', 'skip'])
        self.get_id = get_id

    def _format_error(self, label, test, error_text, test_tags=None):
        test_tags = test_tags or ()
        tags = ' '.join(test_tags)
        if tags:
            tags = six.text_type(('tags: %s\n' % tags))
        return six.text_type(''.join([
            self.sep1,
            six.text_type('%s: %s\n' % (label, test.id())),
            tags,
            self.sep2,
            error_text,
            ]))

    def status(self, **kwargs):
        super(CLITestResult, self).status(**kwargs)
        self._summary.status(**kwargs)
        test_status = kwargs.get('test_status')
        test_tags = kwargs.get('test_tags')
        if test_status == 'fail':
            self.stream.write(
                self._format_error(six.text_type('FAIL'),
                                   *(self._summary.errors[-1]),
                                   test_tags=test_tags))
        if test_status not in self.filterable_states:
            return

    def _get_previous_summary(self):
        if self._previous_run is None:
            return None
        previous_summary = SummarizingResult()
        previous_summary.startTestRun()
        test = self._previous_run.get_test()
        test.run(previous_summary)
        previous_summary.stopTestRun()
        return previous_summary

    def _output_summary(self, run_id):
        """Output a test run.

        :param run_id: The run id.
        """
        time = self._summary.get_time_taken()
        time_delta = None
        num_tests_run_delta = None
        num_failures_delta = None
        values = [('id', run_id, None)]
        failures = self._summary.get_num_failures()
        previous_summary = self._get_previous_summary()
        if failures:
            if previous_summary:
                num_failures_delta = failures - \
                    previous_summary.get_num_failures()
            values.append(('failures', failures, num_failures_delta))
        if previous_summary:
            num_tests_run_delta = self._summary.testsRun - \
                previous_summary.testsRun
            if time:
                previous_time_taken = previous_summary.get_time_taken()
                if previous_time_taken:
                    time_delta = time - previous_time_taken
        skips = len(self._summary.skipped)
        if skips:
            values.append(('skips', skips, None))
        output.output_summary(
            not bool(failures), self._summary.testsRun, num_tests_run_delta,
            time, time_delta, values, output=self.stream)

    def startTestRun(self):
        super(CLITestResult, self).startTestRun()
        self._summary.startTestRun()

    def stopTestRun(self):
        super(CLITestResult, self).stopTestRun()
        run_id = self.get_id()
        self._summary.stopTestRun()
        self._output_summary(run_id)

    def get_summary(self):
        return self._summary
