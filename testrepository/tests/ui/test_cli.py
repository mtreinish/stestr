# -*- encoding: utf-8 -*-
#
# Copyright (c) 2009, 2010 Testrepository Contributors
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

"""Tests for UI support logic and the UI contract."""

import doctest
from io import BytesIO, StringIO, TextIOWrapper
import optparse
import os
import sys
from textwrap import dedent

from fixtures import EnvironmentVariable
import subunit
import testtools
from testtools import TestCase
from testtools.compat import _b, _u
from testtools.matchers import (
    DocTestMatches,
    MatchesException,
    )

from testrepository import arguments
from testrepository import commands
from testrepository.commands import run
from testrepository.ui import cli
from testrepository.tests import ResourcedTestCase, StubTestCommand


def get_test_ui_and_cmd(options=(), args=()):
    stdout = TextIOWrapper(BytesIO(), 'utf8', line_buffering=True)
    stdin = StringIO()
    stderr = StringIO()
    argv = list(args)
    for option, value in options:
        # only bool handled so far
        if value:
            argv.append('--%s' % option)
    ui = cli.UI(argv, stdin, stdout, stderr)
    cmd = run.run(ui)
    ui.set_command(cmd)
    return ui, cmd


class TestCLIUI(ResourcedTestCase):

    def setUp(self):
        super(TestCLIUI, self).setUp()
        self.useFixture(EnvironmentVariable('TESTR_PDB'))

    def test_construct(self):
        stdout = BytesIO()
        stdin = BytesIO()
        stderr = BytesIO()
        cli.UI([], stdin, stdout, stderr)

    def test_stream_comes_from_stdin(self):
        stdout = BytesIO()
        stdin = BytesIO(_b('foo\n'))
        stderr = BytesIO()
        ui = cli.UI([], stdin, stdout, stderr)
        cmd = commands.Command(ui)
        cmd.input_streams = ['subunit']
        ui.set_command(cmd)
        results = []
        for stream in ui.iter_streams('subunit'):
            results.append(stream.read())
        self.assertEqual([_b('foo\n')], results)

    def test_dash_d_sets_here_option(self):
        stdout = BytesIO()
        stdin = BytesIO(_b('foo\n'))
        stderr = BytesIO()
        ui = cli.UI(['-d', '/nowhere/'], stdin, stdout, stderr)
        cmd = commands.Command(ui)
        ui.set_command(cmd)
        self.assertEqual('/nowhere/', ui.here)

    def test_outputs_error_string(self):
        try:
            raise Exception('fooo')
        except Exception:
            err_tuple = sys.exc_info()
        expected = str(err_tuple[1]) + '\n'
        stdout = StringIO()
        stdin = StringIO()
        stderr = StringIO()
        ui = cli.UI([], stdin, stdout, stderr)
        ui.output_error(err_tuple)
        self.assertThat(stderr.getvalue(), DocTestMatches(expected))

    def test_error_enters_pdb_when_TESTR_PDB_set(self):
        os.environ['TESTR_PDB'] = '1'
        try:
            raise Exception('fooo')
        except Exception:
            err_tuple = sys.exc_info()
        expected = dedent("""\
              File "...test_cli.py", line ..., in ...pdb_when_TESTR_PDB_set
                raise Exception('fooo')
            <BLANKLINE>
            fooo
            """)
        stdout = StringIO()
        stdin = StringIO(_u('c\n'))
        stderr = StringIO()
        ui = cli.UI([], stdin, stdout, stderr)
        ui.output_error(err_tuple)
        self.assertThat(stderr.getvalue(),
            DocTestMatches(expected, doctest.ELLIPSIS))

    def test_outputs_rest_to_stdout(self):
        ui, cmd = get_test_ui_and_cmd()
        ui.output_rest(_u('topic\n=====\n'))
        self.assertEqual(_b('topic\n=====\n'), ui._stdout.buffer.getvalue())

    def test_outputs_results_to_stdout(self):
        ui, cmd = get_test_ui_and_cmd()
        class Case(ResourcedTestCase):
            def method(self):
                self.fail('quux')
        result, summary = ui.make_result(lambda: None, StubTestCommand())
        result.startTestRun()
        Case('method').run(testtools.ExtendedToStreamDecorator(result))
        result.stopTestRun()
        self.assertThat(ui._stdout.buffer.getvalue().decode('utf8'),
            DocTestMatches("""\
======================================================================
FAIL: testrepository.tests.ui.test_cli.Case.method
----------------------------------------------------------------------
...Traceback (most recent call last):...
  File "...test_cli.py", line ..., in method
    self.fail(\'quux\')
AssertionError: quux...
""", doctest.ELLIPSIS))

    def test_outputs_stream_to_stdout(self):
        ui, cmd = get_test_ui_and_cmd()
        stream = BytesIO(_b("Foo \n bar"))
        ui.output_stream(stream)
        self.assertEqual(_b("Foo \n bar"), ui._stdout.buffer.getvalue())

    def test_outputs_tables_to_stdout(self):
        ui, cmd = get_test_ui_and_cmd()
        ui.output_table([('foo', 1), ('b', 'quux')])
        self.assertEqual(_b('foo  1\n---  ----\nb    quux\n'),
            ui._stdout.buffer.getvalue())

    def test_outputs_tests_to_stdout(self):
        ui, cmd = get_test_ui_and_cmd()
        ui.output_tests([self, self.__class__('test_construct')])
        self.assertThat(
            ui._stdout.buffer.getvalue().decode('utf8'),
            DocTestMatches(
                '...TestCLIUI.test_outputs_tests_to_stdout\n'
                '...TestCLIUI.test_construct\n', doctest.ELLIPSIS))

    def test_outputs_values_to_stdout(self):
        ui, cmd = get_test_ui_and_cmd()
        ui.output_values([('foo', 1), ('bar', 'quux')])
        self.assertEqual(_b('foo=1, bar=quux\n'), ui._stdout.buffer.getvalue())

    def test_outputs_summary_to_stdout(self):
        ui, cmd = get_test_ui_and_cmd()
        summary = [True, 1, None, 2, None, []]
        expected_summary = ui._format_summary(*summary)
        ui.output_summary(*summary)
        self.assertEqual(_b("%s\n" % (expected_summary,)),
            ui._stdout.buffer.getvalue())

    def test_parse_error_goes_to_stderr(self):
        stdout = StringIO()
        stdin = StringIO()
        stderr = StringIO()
        ui = cli.UI(['one'], stdin, stdout, stderr)
        cmd = commands.Command(ui)
        cmd.args = [arguments.command.CommandArgument('foo')]
        ui.set_command(cmd)
        self.assertEqual("Could not find command 'one'.\n", stderr.getvalue())

    def test_parse_excess_goes_to_stderr(self):
        stdout = StringIO()
        stdin = StringIO()
        stderr = StringIO()
        ui = cli.UI(['one'], stdin, stdout, stderr)
        cmd = commands.Command(ui)
        ui.set_command(cmd)
        self.assertEqual("Unexpected arguments: ['one']\n", stderr.getvalue())

    def test_parse_options_after_double_dash_are_arguments(self):
        stdout = BytesIO()
        stdin = BytesIO()
        stderr = BytesIO()
        ui = cli.UI(['one', '--', '--two', 'three'], stdin, stdout, stderr)
        cmd = commands.Command(ui)
        cmd.args = [arguments.string.StringArgument('myargs', max=None),
            arguments.doubledash.DoubledashArgument(),
            arguments.string.StringArgument('subargs', max=None)]
        ui.set_command(cmd)
        self.assertEqual({
            'doubledash': ['--'],
            'myargs': ['one'],
            'subargs': ['--two', 'three']},
            ui.arguments)

    def test_double_dash_passed_to_arguments(self):
        class CaptureArg(arguments.AbstractArgument):
            def _parse_one(self, arg):
                return arg
        stdout = BytesIO()
        stdin = BytesIO()
        stderr = BytesIO()
        ui = cli.UI(['one', '--', '--two', 'three'], stdin, stdout, stderr)
        cmd = commands.Command(ui)
        cmd.args = [CaptureArg('args', max=None)]
        ui.set_command(cmd)
        self.assertEqual({'args':['one', '--', '--two', 'three']}, ui.arguments)

    def test_run_subunit_option(self):
        ui, cmd = get_test_ui_and_cmd(options=[('subunit', True)])
        self.assertEqual(True, ui.options.subunit)

    def test_dash_dash_help_shows_help(self):
        stdout = StringIO()
        stdin = StringIO()
        stderr = StringIO()
        ui = cli.UI(['--help'], stdin, stdout, stderr)
        cmd = commands.Command(ui)
        cmd.args = [arguments.string.StringArgument('foo')]
        cmd.name = "bar"
        # By definition SystemExit is not caught by 'except Exception'.
        try:
            ui.set_command(cmd)
        except SystemExit:
            exc_info = sys.exc_info()
            self.assertThat(exc_info, MatchesException(SystemExit(0)))
        else:
            self.fail('ui.set_command did not raise')
        self.assertThat(stdout.getvalue(),
            DocTestMatches("""Usage: run.py bar [options] foo
...
A command that can be run...
...
  -d HERE, --here=HERE...
...""", doctest.ELLIPSIS))

class TestCLISummary(TestCase):

    def get_summary(self, successful, tests, tests_delta, time, time_delta, values):
        """Get the summary that would be output for successful & values."""
        ui, cmd = get_test_ui_and_cmd()
        return ui._format_summary(
            successful, tests, tests_delta, time, time_delta, values)

    def test_success_only(self):
        x = self.get_summary(True, None, None, None, None, [])
        self.assertEqual('PASSED', x)

    def test_failure_only(self):
        x = self.get_summary(False, None, None, None, None, [])
        self.assertEqual('FAILED', x)

    def test_time(self):
        x = self.get_summary(True, None, None, 3.4, None, [])
        self.assertEqual('Ran tests in 3.400s\nPASSED', x)

    def test_time_with_delta(self):
        x = self.get_summary(True, None, None, 3.4, 0.1, [])
        self.assertEqual('Ran tests in 3.400s (+0.100s)\nPASSED', x)

    def test_tests_run(self):
        x = self.get_summary(True, 34, None, None, None, [])
        self.assertEqual('Ran 34 tests\nPASSED', x)

    def test_tests_run_with_delta(self):
        x = self.get_summary(True, 34, 5, None, None, [])
        self.assertEqual('Ran 34 (+5) tests\nPASSED', x)

    def test_tests_and_time(self):
        x = self.get_summary(True, 34, -5, 3.4, 0.1, [])
        self.assertEqual('Ran 34 (-5) tests in 3.400s (+0.100s)\nPASSED', x)

    def test_other_values(self):
        x = self.get_summary(
            True, None, None, None, None, [('failures', 12, -1), ('errors', 13, 2)])
        self.assertEqual('PASSED (failures=12 (-1), errors=13 (+2))', x)

    def test_values_no_delta(self):
        x = self.get_summary(
            True, None, None, None, None,
            [('failures', 12, None), ('errors', 13, None)])
        self.assertEqual('PASSED (failures=12, errors=13)', x)

    def test_combination(self):
        x = self.get_summary(
            True, 34, -5, 3.4, 0.1, [('failures', 12, -1), ('errors', 13, 2)])
        self.assertEqual(
            ('Ran 34 (-5) tests in 3.400s (+0.100s)\n'
             'PASSED (failures=12 (-1), errors=13 (+2))'), x)


class TestCLITestResult(TestCase):

    def make_exc_info(self):
        # Make an exc_info tuple for use in testing.
        try:
            1/0
        except ZeroDivisionError:
            return sys.exc_info()

    def make_result(self, stream=None, argv=None, filter_tags=None):
        if stream is None:
            stream = BytesIO()
        argv = argv or []
        ui = cli.UI(argv, None, stream, None)
        cmd = commands.Command(ui)
        cmd.options = [
            optparse.Option("--subunit", action="store_true",
                default=False, help="Display results in subunit format."),
            ]
        ui.set_command(cmd)
        return ui.make_result(
            lambda: None, StubTestCommand(filter_tags=filter_tags))

    def test_initial_stream(self):
        # CLITestResult.__init__ does not do anything to the stream it is
        # given.
        stream = StringIO()
        cli.CLITestResult(cli.UI(None, None, None, None), stream, lambda: None)
        self.assertEqual('', stream.getvalue())

    def _unwrap(self, result):
        """Unwrap result to get to the CLI result object."""
        return result.decorated.decorated

    def test_format_error(self):
        # CLITestResult formats errors by giving them a big fat line, a title
        # made up of their 'label' and the name of the test, another different
        # big fat line, and then the actual error itself.
        result = self._unwrap(self.make_result()[0])
        error = result._format_error('label', self, 'error text')
        expected = '%s%s: %s\n%s%s' % (
            result.sep1, 'label', self.id(), result.sep2, 'error text')
        self.assertThat(error, DocTestMatches(expected))

    def test_format_error_includes_tags(self):
        result1 = self.make_result()
        result = self._unwrap(result1[0])
        #result1.startTestRun()
        #result1.status(test_id=self.id(), test_status='fail', eof=True,
        #    test_tags=set(['foo']), file_name='traceback',
        #    mime_type='test/plain;charset=utf8', file_bytes=b'error text')
        result.tags(set(['foo']), set())
        error = result._format_error('label', self, 'error text')
        expected = '%s%s: %s\ntags: foo\n%s%s' % (
            result.sep1, 'label', self.id(), result.sep2, 'error text')
        self.assertThat(error, DocTestMatches(expected))

    def test_addFail_outputs_error(self):
        # CLITestResult.status test_status='fail' outputs the given error
        # immediately to the stream.
        stream = StringIO()
        result = self.make_result(stream)[0]
        error = self.make_exc_info()
        error_text = 'foo\nbar\n'
        result.startTestRun()
        result.status(test_id=self.id(), test_status='fail', eof=True,
            file_name='traceback', mime_type='text/plain;charset=utf8',
            file_bytes=error_text.encode('utf8'))
        result1 = self._unwrap(result)
        self.assertThat(
            stream.getvalue(),
            DocTestMatches(result1._format_error('FAIL', self, error_text)))

    def test_addFailure_handles_string_encoding(self):
        # CLITestResult.addFailure outputs the given error handling non-ascii
        # characters.
        # Lets say we have bytes output, not string for some reason.
        stream = BytesIO()
        result = self.make_result(stream)[0]
        result.startTestRun()
        result.status(test_id='foo', test_status='fail', file_name='traceback',
            mime_type='text/plain;charset=utf8',
            file_bytes=b'-->\xe2\x80\x9c<--', eof=True)
        pattern = _u("...-->?<--...")
        self.assertThat(
            stream.getvalue().decode('utf8'),
            DocTestMatches(pattern, doctest.ELLIPSIS))

    def test_subunit_output(self):
        bytestream = BytesIO()
        stream = TextIOWrapper(bytestream, 'utf8', line_buffering=True)
        result = self.make_result(stream, argv=['--subunit'])[0]
        result.startTestRun()
        result.stopTestRun()
        self.assertEqual(b'', bytestream.getvalue())

    def test_make_result_tag_filter(self):
        stream = StringIO()
        result, summary = self.make_result(
            stream, filter_tags=set(['worker-0']))
        # Generate a bunch of results with tags in the same events that
        # testtools generates them.
        tags = set(['worker-0'])
        result.startTestRun()
        result.status(test_id='pass', test_status='inprogress')
        result.status(test_id='pass', test_status='success', test_tags=tags)
        result.status(test_id='fail', test_status='inprogress')
        result.status(test_id='fail', test_status='fail', test_tags=tags)
        result.status(test_id='xfail', test_status='inprogress')
        result.status(test_id='xfail', test_status='xfail', test_tags=tags)
        result.status(test_id='uxsuccess', test_status='inprogress')
        result.status(
            test_id='uxsuccess', test_status='uxsuccess', test_tags=tags)
        result.status(test_id='skip', test_status='inprogress')
        result.status(test_id='skip', test_status='skip', test_tags=tags)
        result.stopTestRun()
        self.assertEqual("""\
======================================================================
FAIL: fail
tags: worker-0
----------------------------------------------------------------------
Ran 1 tests
FAILED (id=None, failures=1)
""", stream.getvalue())

