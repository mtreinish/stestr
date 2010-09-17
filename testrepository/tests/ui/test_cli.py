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
import sys

from testtools.matchers import DocTestMatches

from testrepository import arguments
import testrepository.arguments.command
from testrepository import commands
from testrepository.ui import cli
from testrepository.tests import ResourcedTestCase


class TestCLIUI(ResourcedTestCase):

    def get_test_ui_and_cmd(self):
        stdout = StringIO()
        stdin = StringIO()
        stderr = StringIO()
        ui = cli.UI([], stdin, stdout, stderr)
        cmd = commands.Command(ui)
        ui.set_command(cmd)
        return ui, cmd

    def test_construct(self):
        stdout = StringIO()
        stdin = StringIO()
        stderr = StringIO()
        ui = cli.UI([], stdin, stdout, stderr)

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

    def test_outputs_rest_to_stdout(self):
        ui, cmd = self.get_test_ui_and_cmd()
        ui.output_rest('topic\n=====\n')
        self.assertEqual('topic\n=====\n', ui._stdout.getvalue())

    def test_outputs_results_to_stdout(self):
        ui, cmd = self.get_test_ui_and_cmd()
        class Case(ResourcedTestCase):
            def method(self):
                self.fail('quux')
        ui.output_results(Case('method'))
        self.assertThat(ui._stdout.getvalue(),DocTestMatches(
            """======================================================================
FAIL: testrepository.tests.ui.test_cli.Case.method
----------------------------------------------------------------------
Text attachment: traceback
------------
Traceback (most recent call last):
...
  File "...test_cli.py", line ..., in method
    self.fail(\'quux\')
AssertionError: quux
------------
""", doctest.ELLIPSIS))

    def test_outputs_stream_to_stdout(self):
        ui, cmd = self.get_test_ui_and_cmd()
        stream = StringIO("Foo \n bar")
        ui.output_stream(stream)
        self.assertEqual("Foo \n bar", ui._stdout.getvalue())

    def test_outputs_tables_to_stdout(self):
        ui, cmd = self.get_test_ui_and_cmd()
        ui.output_table([('foo', 1), ('b', 'quux')])
        self.assertEqual('foo  1\n---  ----\nb    quux\n',
            ui._stdout.getvalue())

    def test_outputs_tests_to_stdout(self):
        ui, cmd = self.get_test_ui_and_cmd()
        ui.output_tests([self, self.__class__('test_construct')])
        self.assertThat(
            ui._stdout.getvalue(),
            DocTestMatches(
                '...TestCLIUI.test_outputs_tests_to_stdout\n'
                '...TestCLIUI.test_construct\n', doctest.ELLIPSIS))

    def test_outputs_values_to_stdout(self):
        ui, cmd = self.get_test_ui_and_cmd()
        ui.output_values([('foo', 1), ('bar', 'quux')])
        self.assertEqual('foo=1, bar=quux\n', ui._stdout.getvalue())

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

    def test_parse_after_double_dash_are_arguments(self):
        stdout = StringIO()
        stdin = StringIO()
        stderr = StringIO()
        ui = cli.UI(['one', '--', '--two', 'three'], stdin, stdout, stderr)
        cmd = commands.Command(ui)
        cmd.args = [arguments.string.StringArgument('args', max=None)]
        ui.set_command(cmd)
        self.assertEqual({'args':['one', '--two', 'three']}, ui.arguments)
