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

import sys

import six
import subunit
import testtools


def output_table(table, output=sys.stdout):
    """Display a table of information.

    :param table: A list of sets representing each row in the table. Each
        element in the set represents a column in the table.
    :param output: The output file object to write the table to. By default
        this is sys.stdout
    """
    # stringify
    contents = []
    for row in table:
        new_row = []
        for column in row:
            new_row.append(str(column))
        contents.append(new_row)
    if not contents:
        return
    widths = [0] * len(contents[0])
    for row in contents:
        for idx, column in enumerate(row):
            if widths[idx] < len(column):
                widths[idx] = len(column)
    # Show a row
    outputs = []

    def show_row(row):
        for idx, column in enumerate(row):
            outputs.append(column)
            if idx == len(row) - 1:
                outputs.append('\n')
                return
            # spacers for the next column
            outputs.append(' ' * (widths[idx] - len(column)))
            outputs.append('  ')

    show_row(contents[0])
    # title spacer
    for idx, width in enumerate(widths):
        outputs.append('-' * width)
        if idx == len(widths) - 1:
            outputs.append('\n')
            continue
        outputs.append('  ')
    for row in contents[1:]:
        show_row(row)
    output.write(six.text_type('').join(outputs))


def output_tests(tests, output=sys.stdout):
    """Display a list of tests.

    :param tests: A list of test objects to output
    :param output: The output file object to write the list to. By default
        this is sys.stdout
    """

    for test in tests:
        id_str = test.id()
        output.write(id_str)
        output.write(six.text_type('\n'))


def make_result(get_id, output=sys.stdout):
    serializer = subunit.StreamResultToBytes(output)
    # By pass user transforms - just forward it all,
    result = serializer
    # and interpret everything as success.
    summary = testtools.StreamSummary()
    summary.startTestRun()
    summary.stopTestRun()
    return result, summary


def output_summary(successful, tests, tests_delta, time, time_delta, values,
                   output=sys.stdout):
    """Display a summary view for the test run.

    :param bool successful: Was the test run successful
    :param int tests: The number of tests that ran
    :param int tests_delta: The change in the number of tests that ran since
        the last run
    :param float time: The number of seconds that it took for the run to
        execute
    :param float time_delta: The change in run time since the last run
    :param values: A list of sets that are used for a breakdown of statuses
        other than success. Each set is in the format:
        (status, number of tests, change in number of tests).
    :param output: The output file object to use. This defaults to stdout
    """
    summary = []
    a = summary.append
    if tests:
        a("Ran %s" % (tests,))
        if tests_delta:
            a(" (%+d)" % (tests_delta,))
        a(" tests")
    if time:
        if not summary:
            a("Ran tests")
        a(" in %0.3fs" % (time,))
        if time_delta:
            a(" (%+0.3fs)" % (time_delta,))
    if summary:
        a("\n")
    if successful:
        a('PASSED')
    else:
        a('FAILED')
    if values:
        a(' (')
        values_strings = []
        for name, value, delta in values:
            value_str = '%s=%s' % (name, value)
            if delta:
                value_str += ' (%+d)' % (delta,)
            values_strings.append(value_str)
        a(', '.join(values_strings))
        a(')')
    output.write(six.text_type(''.join(summary)) + six.text_type('\n'))


def output_stream(stream, output=sys.stdout):
        _binary_stdout = subunit.make_stream_binary(output)
        contents = stream.read(65536)
        assert type(contents) is bytes, \
            "Bad stream contents %r" % type(contents)
        # If there are unflushed bytes in the text wrapper, we need to sync..
        output.flush()
        while contents:
            _binary_stdout.write(contents)
            contents = stream.read(65536)
        _binary_stdout.flush()


class ReturnCodeToSubunit(object):
    """Converts a process return code to a subunit error on the process stdout.

    The ReturnCodeToSubunit object behaves as a read-only stream, supplying
    the read, readline and readlines methods. If the process exits non-zero a
    synthetic test is added to the output, making the error accessible to
    subunit stream consumers. If the process closes its stdout and then does
    not terminate, reading from the ReturnCodeToSubunit stream will hang.

    :param process: A subprocess.Popen object that is
        generating subunit.
    """

    def __init__(self, process):
        """Adapt a process to a readable stream."""
        self.proc = process
        self.done = False
        self.source = self.proc.stdout
        self.lastoutput = six.binary_type(('\n').encode('utf8')[0])

    def _append_return_code_as_test(self):
        if self.done is True:
            return
        self.source = six.BytesIO()
        returncode = self.proc.wait()
        if returncode != 0:
            if self.lastoutput != six.binary_type(('\n').encode('utf8')[0]):
                # Subunit V1 is line orientated, it has to start on a fresh
                # line. V2 needs to start on any fresh utf8 character border
                # - which is not guaranteed in an arbitrary stream endpoint, so
                # injecting a \n gives us such a guarantee.
                self.source.write(six.binary_type('\n'))
            stream = subunit.StreamResultToBytes(self.source)
            stream.status(test_id='process-returncode', test_status='fail',
                          file_name='traceback',
                          mime_type='text/plain;charset=utf8',
                          file_bytes=(
                              'returncode %d' % returncode).encode('utf8'))
        self.source.seek(0)
        self.done = True

    def read(self, count=-1):
        if count == 0:
            return six.text_type('')
        result = self.source.read(count)
        if result:
            self.lastoutput = result[-1]
            return result
        self._append_return_code_as_test()
        return self.source.read(count)

    def readline(self):
        result = self.source.readline()
        if result:
            self.lastoutput = result[-1]
            return result
        self._append_return_code_as_test()
        return self.source.readline()

    def readlines(self):
        result = self.source.readlines()
        if result:
            self.lastoutput = result[-1][-1]
        self._append_return_code_as_test()
        result.extend(self.source.readlines())
        return result
