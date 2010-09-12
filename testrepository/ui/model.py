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

"""Am object based UI for testrepository."""

from cStringIO import StringIO
import optparse

from testrepository import ui
from testtools import TestResult


class ProcessModel(object):
    """A subprocess.Popen test double."""

    def __init__(self, ui):
        self.ui = ui
        self.returncode = 0

    def communicate(self):
        self.ui.outputs.append(('communicate',))
        return '', ''


class TestSuiteModel(object):

    def __init__(self):
        self._results = []

    def recordResult(self, method, *args):
        self._results.append((method, args))

    def run(self, result):
        for method, args in self._results:
            getattr(result, method)(*args)


class TestResultModel(TestResult):

    def __init__(self, ui):
        super(TestResultModel, self).__init__()
        self.ui = ui
        self._suite = TestSuiteModel()

    def startTest(self, test):
        self._suite.recordResult('startTest', test)

    def stopTest(self, test):
        self._suite.recordResult('stopTest', test)

    def addError(self, test, *args):
        super(TestResultModel, self).addError(test, *args)
        self._suite.recordResult('addError', test, *args)

    def addFailure(self, test, *args):
        super(TestResultModel, self).addFailure(test, *args)
        self._suite.recordResult('addFailure', test, *args)

    def stopTestRun(self):
        if self.wasSuccessful():
            return
        if self.ui.options.quiet:
            return
        self.ui.outputs.append(('results', self._suite))


class UI(ui.AbstractUI):
    """A object based UI.
    
    This is useful for reusing the Command objects that provide a simplified
    interaction model with the domain logic from python. It is used for
    testing testrepository commands.
    """

    def __init__(self, input_streams=None, options=(), args={}):
        """Create a model UI.

        :param input_streams: A list of stream name, bytes stream tuples to be
            used as the available input streams for this ui.
        :param options: Options to explicitly set values for.
        :param args: The argument values to give the UI.
        """
        self.input_streams = {}
        if input_streams:
            for stream_type, stream_bytes in input_streams:
                self.input_streams.setdefault(stream_type, []).append(
                    stream_bytes)
        self.here = 'memory:'
        self.unparsed_opts = options
        self.outputs = []
        # Could take parsed args, but for now this is easier.
        self.unparsed_args = args

    def _check_cmd(self):
        options = list(self.unparsed_opts)
        self.options = optparse.Values()
        seen_options = set()
        for option, value in options:
            setattr(self.options, option, value)
            seen_options.add(option)
        if not 'quiet' in seen_options:
            setattr(self.options, 'quiet', False)
        for option in self.cmd.options:
            if not option.dest in seen_options:
                setattr(self.options, option.dest, option.default)
        args = list(self.unparsed_args)
        parsed_args = {}
        failed = False
        for arg in self.cmd.args:
            try:
                parsed_args[arg.name] = arg.parse(args)
            except ValueError:
                failed = True
                break
        self.arguments = parsed_args
        return args == [] and not failed

    def _iter_streams(self, stream_type):
        streams = self.input_streams.pop(stream_type, [])
        for stream_bytes in streams:
            yield StringIO(stream_bytes)

    def make_result(self, get_id):
        return TestResultModel(self)

    def output_error(self, error_tuple):
        self.outputs.append(('error', error_tuple))

    def output_rest(self, rest_string):
        self.outputs.append(('rest', rest_string))

    def output_stream(self, stream):
        self.outputs.append(('stream', stream.read()))

    def output_table(self, table):
        self.outputs.append(('table', table))

    def output_tests(self, tests):
        """Output a list of tests."""
        self.outputs.append(('tests', tests))

    def output_values(self, values):
        self.outputs.append(('values', values))

    def subprocess_Popen(self, *args, **kwargs):
        # Really not an output - outputs should be renamed to events.
        self.outputs.append(('popen', args, kwargs))
        return ProcessModel(self)
