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

import sys

import six
import subunit
import testtools


def output_table(table, output=sys.stdout):
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
    for test in tests:
        # On Python 2.6 id() returns bytes.
        id_str = test.id()
        if type(id_str) is bytes:
            id_str = id_str.decode('utf8')
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


def output_values(values, output=sys.stdout):
    outputs = []
    for label, value in values:
        outputs.append('%s=%s' % (label, value))
    output.write(six.text_type('%s\n' % ', '.join(outputs)))


class ReturnCodeToSubunit(object):
    """Converts a process return code to a subunit error on the process stdout.

    The ReturnCodeToSubunit object behaves as a readonly stream, supplying
    the read, readline and readlines methods. If the process exits non-zero a
    synthetic test is added to the output, making the error accessible to
    subunit stream consumers. If the process closes its stdout and then does
    not terminate, reading from the ReturnCodeToSubunit stream will hang.

    This class will be deleted at some point, allowing parsing to read from the
    actual fd and benefit from select for aggregating non-subunit output.
    """

    def __init__(self, process):
        """Adapt a process to a readable stream.

        :param process: A subprocess.Popen object that is
            generating subunit.
        """
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
            return six.binary_type('')
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
