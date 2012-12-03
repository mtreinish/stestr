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
from cStringIO import StringIO
import optparse
import os
import sys
from textwrap import dedent

from fixtures import EnvironmentVariable
import subunit
from testtools import TestCase
from testtools.matchers import DocTestMatches

from testrepository import arguments
from testrepository import commands
from testrepository.commands import run
from testrepository.ui import cli
from testrepository.tests import ResourcedTestCase, StubTestCommand


def get_test_ui_and_cmd(options=(), args=()):
    stdout = StringIO()
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
        stdout = StringIO()
        stdin = StringIO()
        stderr = StringIO()
        cli.UI([], stdin, stdout, stderr)

    def test_stream_comes_from_stdin(self):
        stdout = StringIO()
        stdin = StringIO('foo\n')
        stderr = StringIO()
        ui = cli.UI([], stdin, stdout, stderr)
        cmd = commands.Command(ui)
        cmd.input_streams = ['subunit']
        ui.set_command(cmd)
        results = []
        for stream in ui.iter_streams('subunit'):
            results.append(stream.read())
        self.assertEqual(['foo\n'], results)

    def test_dash_d_sets_here_option(self):
        stdout = StringIO()
        stdin = StringIO('foo\n')
        stderr = StringIO()
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
        stdin = StringIO('c\n')
        stderr = StringIO()
        ui = cli.UI([], stdin, stdout, stderr)
        ui.output_error(err_tuple)
        self.assertThat(stderr.getvalue(),
            DocTestMatches(expected, doctest.ELLIPSIS))

    def test_outputs_rest_to_stdout(self):
        ui, cmd = get_test_ui_and_cmd()
        ui.output_rest('topic\n=====\n')
        self.assertEqual('topic\n=====\n', ui._stdout.getvalue())

    def test_outputs_results_to_stdout(self):
        ui, cmd = get_test_ui_and_cmd()
        class Case(ResourcedTestCase):
            def method(self):
                self.fail('quux')
        result = ui.make_result(lambda: None, StubTestCommand())
        Case('method').run(result)
        self.assertThat(ui._stdout.getvalue(),DocTestMatches(
            """======================================================================
FAIL: testrepository.tests.ui.test_cli.Case.method
----------------------------------------------------------------------
...Traceback (most recent call last):...
  File "...test_cli.py", line ..., in method
    self.fail(\'quux\')
AssertionError: quux...
""", doctest.ELLIPSIS))

    def test_outputs_stream_to_stdout(self):
        ui, cmd = get_test_ui_and_cmd()
        stream = StringIO("Foo \n bar")
        ui.output_stream(stream)
        self.assertEqual("Foo \n bar", ui._stdout.getvalue())

    def test_outputs_tables_to_stdout(self):
        ui, cmd = get_test_ui_and_cmd()
        ui.output_table([('foo', 1), ('b', 'quux')])
        self.assertEqual('foo  1\n---  ----\nb    quux\n',
            ui._stdout.getvalue())

    def test_outputs_tests_to_stdout(self):
        ui, cmd = get_test_ui_and_cmd()
        ui.output_tests([self, self.__class__('test_construct')])
        self.assertThat(
            ui._stdout.getvalue(),
            DocTestMatches(
                '...TestCLIUI.test_outputs_tests_to_stdout\n'
                '...TestCLIUI.test_construct\n', doctest.ELLIPSIS))

    def test_outputs_values_to_stdout(self):
        ui, cmd = get_test_ui_and_cmd()
        ui.output_values([('foo', 1), ('bar', 'quux')])
        self.assertEqual('foo=1, bar=quux\n', ui._stdout.getvalue())

    def test_outputs_summary_to_stdout(self):
        ui, cmd = get_test_ui_and_cmd()
        summary = [True, 1, None, 2, None, []]
        expected_summary = ui._format_summary(*summary)
        ui.output_summary(*summary)
        self.assertEqual("%s\n" % (expected_summary,), ui._stdout.getvalue())

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
        stdout = StringIO()
        stdin = StringIO()
        stderr = StringIO()
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
        stdout = StringIO()
        stdin = StringIO()
        stderr = StringIO()
        ui = cli.UI(['one', '--', '--two', 'three'], stdin, stdout, stderr)
        cmd = commands.Command(ui)
        cmd.args = [CaptureArg('args', max=None)]
        ui.set_command(cmd)
        self.assertEqual({'args':['one', '--', '--two', 'three']}, ui.arguments)

    def test_run_subunit_option(self):
        ui, cmd = get_test_ui_and_cmd(options=[('subunit', True)])
        self.assertEqual(True, ui.options.subunit)

    def test_subunit_output_with_full_results(self):
        # When --full-results is passed in, successes are included in the
        # subunit output.
        ui, cmd = get_test_ui_and_cmd(options=[('subunit', True)])
        stream = StringIO()
        subunit_result = subunit.TestProtocolClient(stream)
        subunit_result.startTest(self)
        subunit_result.addSuccess(self)
        subunit_result.stopTest(self)
        result = ui.make_result(lambda: None, StubTestCommand())
        result.startTest(self)
        result.addSuccess(self)
        result.stopTest(self)
        self.assertEqual(stream.getvalue(), ui._stdout.getvalue())


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

    def make_result(self, stream=None, fullresults=False):
        if stream is None:
            stream = StringIO()
        argv = []
        if fullresults:
            argv.append('--full-results')
        ui = cli.UI(argv, None, stream, None)
        cmd = commands.Command(ui)
        if fullresults:
            cmd.options = [optparse.Option(
                "--full-results", action="store_true", default=False,
                help="Show full results.")]
        ui.set_command(cmd)
        return ui.make_result(lambda: None, StubTestCommand())

    def test_initial_stream(self):
        # CLITestResult.__init__ does not do anything to the stream it is
        # given.
        stream = StringIO()
        cli.CLITestResult(cli.UI(None, None, None, None), stream, lambda: None)
        self.assertEqual('', stream.getvalue())

    def test_format_error(self):
        # CLITestResult formats errors by giving them a big fat line, a title
        # made up of their 'label' and the name of the test, another different
        # big fat line, and then the actual error itself.
        result = self.make_result(fullresults=True)
        error = result._format_error('label', self, 'error text')
        expected = '%s%s: %s\n%s%s' % (
            result.sep1, 'label', self.id(), result.sep2, 'error text')
        self.assertThat(error, DocTestMatches(expected))

    def test_addError_outputs_error(self):
        # CLITestResult.addError outputs the given error immediately to the
        # stream.
        stream = StringIO()
        result = self.make_result(stream, fullresults=True)
        error = self.make_exc_info()
        error_text = result._err_details_to_string(self, error)
        result.addError(self, error)
        self.assertThat(
            stream.getvalue(),
            DocTestMatches(result._format_error('ERROR', self, error_text)))

    def test_addFailure_outputs_failure(self):
        # CLITestResult.addFailure outputs the given error immediately to the
        # stream.
        stream = StringIO()
        result = self.make_result(stream, fullresults=True)
        error = self.make_exc_info()
        error_text = result._err_details_to_string(self, error)
        result.addFailure(self, error)
        self.assertThat(
            stream.getvalue(),
            DocTestMatches(result._format_error('FAIL', self, error_text)))

    def test_addFailure_handles_string_encoding(self):
        # CLITestResult.addFailure outputs the given error handling non-ascii
        # characters.
        stream = StringIO()
        result = self.make_result(stream, fullresults=True)
        class MyError(ValueError):
            def __unicode__(self):
                return u'\u201c'
        error = (MyError, MyError(), None)
        result.addFailure(self, error)
        self.assertThat(
            stream.getvalue(),
            DocTestMatches("...MyError: ?", doctest.ELLIPSIS))
