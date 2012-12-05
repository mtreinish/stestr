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

import os
import signal
import subunit
import sys

from testtools.compat import unicode_output_stream

from testrepository import ui
from testrepository.commands import get_command_parser
from testrepository.results import TestResultFilter


class CLITestResult(ui.BaseUITestResult):
    """A TestResult for the CLI."""

    def __init__(self, ui, get_id, stream, previous_run=None):
        """Construct a CLITestResult writing to stream."""
        super(CLITestResult, self).__init__(ui, get_id, previous_run)
        self.stream = unicode_output_stream(stream)
        self.sep1 = u'=' * 70 + '\n'
        self.sep2 = u'-' * 70 + '\n'

    def _format_error(self, label, test, error_text):
        tags = u' '.join(self.current_tags)
        if tags:
            tags = u'tags: %s\n' % tags
        return u''.join([
            self.sep1,
            u'%s: %s\n' % (label, test.id()),
            tags,
            self.sep2,
            error_text,
            ])

    def addError(self, test, err=None, details=None):
        super(CLITestResult, self).addError(test, err=err, details=details)
        self.stream.write(self._format_error(u'ERROR', *(self.errors[-1])))

    def addFailure(self, test, err=None, details=None):
        super(CLITestResult, self).addFailure(test, err=err, details=details)
        self.stream.write(self._format_error(u'FAIL', *(self.failures[-1])))


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

    def make_result(self, get_id, test_command, previous_run=None):
        if getattr(self.options, 'subunit', False):
            # By pass user transforms - just forward it all.
            return subunit.TestProtocolClient(self._stdout)
        output = CLITestResult(self, get_id, self._stdout, previous_run)
        if getattr(self.options, 'full_results', False):
            return output
        # Apply user defined transforms.
        return test_command.make_result(output)

    def output_error(self, error_tuple):
        if 'TESTR_PDB' in os.environ:
            import traceback
            self._stderr.write(''.join(traceback.format_tb(error_tuple[2])))
            self._stderr.write('\n')
            import pdb;
            p = pdb.Pdb(stdin=self._stdin, stdout=self._stdout)
            p.reset()
            p.interaction(None, error_tuple[2])
        self._stderr.write(str(error_tuple[1]) + '\n')

    def output_rest(self, rest_string):
        self._stdout.write(rest_string)
        if not rest_string.endswith('\n'):
            self._stdout.write('\n')

    def output_stream(self, stream):
        contents = stream.read(65536)
        while contents:
            self._stdout.write(contents)
            contents = stream.read(65536)

    def output_table(self, table):
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
                outputs.append(' '*(widths[idx]-len(column)))
                outputs.append('  ')
        show_row(contents[0])
        # title spacer
        for idx, width in enumerate(widths):
            outputs.append('-'*width)
            if idx == len(widths) - 1:
                outputs.append('\n')
                continue
            outputs.append('  ')
        for row in contents[1:]:
            show_row(row)
        self._stdout.write(''.join(outputs))

    def output_tests(self, tests):
        for test in tests:
            self._stdout.write(test.id())
            self._stdout.write('\n')

    def output_values(self, values):
        outputs = []
        for label, value in values:
            outputs.append('%s=%s' % (label, value))
        self._stdout.write('%s\n' % ', '.join(outputs))

    def _format_summary(self, successful, tests, tests_delta,
                        time, time_delta, values):
        # We build the string by appending to a list of strings and then
        # joining trivially at the end. Avoids expensive string concatenation.
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
        return ''.join(summary)

    def output_summary(self, successful, tests, tests_delta,
                       time, time_delta, values):
        self._stdout.write(
            self._format_summary(
                successful, tests, tests_delta, time, time_delta, values))
        self._stdout.write('\n')

    def _check_cmd(self):
        parser = get_command_parser(self.cmd)
        parser.add_option("-d", "--here", dest="here",
            help="Set the directory or url that a command should run from. "
            "This affects all default path lookups but does not affect paths "
            "supplied to the command.", default=os.getcwd(), type=str)
        parser.add_option("-q", "--quiet", action="store_true", default=False,
            help="Turn off output other than the primary output for a command "
            "and any errors.")
        # yank out --, as optparse makes it silly hard to just preserve it.
        try:
            where_dashdash = self._argv.index('--')
            opt_argv = self._argv[:where_dashdash]
            other_args = self._argv[where_dashdash:]
        except ValueError:
            opt_argv = self._argv
            other_args = []
        if '-h' in opt_argv or '--help' in opt_argv or '-?' in opt_argv:
            self.output_rest(parser.format_help())
            # Fugly, but its what optparse does: we're just overriding the
            # output path.
            raise SystemExit(0)
        options, args = parser.parse_args(opt_argv)
        args += other_args
        self.here = options.here
        self.options = options
        parsed_args = {}
        failed = False
        for arg in self.cmd.args:
            try:
                parsed_args[arg.name] = arg.parse(args)
            except ValueError:
                exc_info = sys.exc_info()
                failed = True
                self._stderr.write("%s\n" % str(exc_info[1]))
                break
        if not failed:
            self.arguments = parsed_args
            if args != []:
                self._stderr.write("Unexpected arguments: %r\n" % args)
        return not failed and args == []

    def _clear_SIGPIPE(self):
        """Clear SIGPIPE : child processes expect the default handler."""
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    def subprocess_Popen(self, *args, **kwargs):
        import subprocess
        if os.name == "posix":
            # GZ 2010-12-04: Should perhaps check for existing preexec_fn and
            #                combine so both will get called.
            kwargs['preexec_fn'] = self._clear_SIGPIPE
        return subprocess.Popen(*args, **kwargs)
