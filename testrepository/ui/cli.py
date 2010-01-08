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

"""A command line UI for testrepository."""

from optparse import OptionParser
import os

import testtools

from testrepository import ui

class CLITestResult(testtools.TestResult):
    """A TestResult for the CLI."""

    def __init__(self, stream):
        """Construct a CLITestResult writing to stream."""
        super(CLITestResult, self).__init__()
        self.stream = stream
        self.sep1 = '=' * 70 + '\n'
        self.sep2 = '-' * 70 + '\n'

    def _show_list(self, label, error_list):
        for test, output in error_list:
            self.stream.write(self.sep1)
            self.stream.write("%s: %s\n" % (label, test.id()))
            self.stream.write(self.sep2)
            self.stream.write(output)

    def stopTestRun(self):
        self._show_list('ERROR', self.errors)
        self._show_list('FAIL', self.failures)
        super(CLITestResult, self).stopTestRun()


class UI(ui.AbstractUI):
    """A command line user interface."""

    def __init__(self, argv, stdin, stdout, stderr):
        """Create a command line UI.

        :param argv: Arguments from the process invocation.
        :param stdin: The stream for stdin.
        :param stdout: The stream for stdout.
        :param stderr: The stream for stderr.
        """
        self._argv = argv
        self._stdin = stdin
        self._stdout = stdout
        self._stderr = stderr

    def _iter_streams(self, stream_type):
        yield self._stdin

    def output_values(self, values):
        outputs = []
        for label, value in values:
            outputs.append('%s: %s' % (label, value))
        self._stdout.write('%s\n' % ' '.join(outputs))

    def output_results(self, suite_or_test):
        result = CLITestResult(self._stdout)
        result.startTestRun()
        try:
            suite_or_test.run(result)
        finally:
            result.stopTestRun()

    def set_command(self, cmd):
        ui.AbstractUI.set_command(self, cmd)
        parser = OptionParser()
        parser.add_option("-d", "--here", dest="here",
            help="Set the directory or url that a command should run from. "
            "This affects all default path lookups but does not affect paths "
            "supplied to the command.", default=os.getcwd(), type=str)
        parser.add_option("-q", "--quiet", action="store_true", default=False,
            help="Turn off output other than the primary output for a command "
            "and any errors.")
        options, args = parser.parse_args(self._argv)
        self.here = options.here
        self.options = options
