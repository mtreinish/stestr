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

from io import BytesIO
import optparse

import testtools

from testrepository import ui


class ProcessModel(object):
    """A subprocess.Popen test double."""

    def __init__(self, ui):
        self.ui = ui
        self.returncode = 0
        self.stdin = BytesIO()
        self.stdout = BytesIO()

    def communicate(self):
        self.ui.outputs.append(('communicate',))
        return self.stdout.getvalue(), b''

    def wait(self):
        return self.returncode


class TestSuiteModel(object):

    def __init__(self):
        self._results = []

    def recordResult(self, method, *args):
        self._results.append((method, args))

    def run(self, result):
        for method, args in self._results:
            getattr(result, method)(*args)


class TestResultModel(ui.BaseUITestResult):

    def __init__(self, ui, get_id, previous_run=None):
        super(TestResultModel, self).__init__(ui, get_id, previous_run)
        self._suite = TestSuiteModel()

    def status(self, test_id=None, test_status=None, test_tags=None,
        runnable=True, file_name=None, file_bytes=None, eof=False,
        mime_type=None, route_code=None, timestamp=None):
        super(TestResultModel, self).status(test_id=test_id,
            test_status=test_status, test_tags=test_tags, runnable=runnable,
            file_name=file_name, file_bytes=file_bytes, eof=eof,
            mime_type=mime_type, route_code=route_code, timestamp=timestamp)
        self._suite.recordResult('status', test_id, test_status)

    def stopTestRun(self):
        if self.ui.options.quiet:
            return
        self.ui.outputs.append(('results', self._suite))
        return super(TestResultModel, self).stopTestRun()


class UI(ui.AbstractUI):
    """A object based UI.
    
    This is useful for reusing the Command objects that provide a simplified
    interaction model with the domain logic from python. It is used for
    testing testrepository commands.
    """

    def __init__(self, input_streams=None, options=(), args=(),
        here='memory:', proc_outputs=(), proc_results=()):
        """Create a model UI.

        :param input_streams: A list of stream name, (file or bytes) tuples to
            be used as the available input streams for this ui.
        :param options: Options to explicitly set values for.
        :param args: The argument values to give the UI.
        :param here: Set the here value for the UI.
        :param proc_outputs: byte strings to be returned in the stdout from
            created processes.
        :param proc_results: numeric exit code to be set in each created
            process.
        """
        self.input_streams = {}
        if input_streams:
            for stream_type, stream_value in input_streams:
                if isinstance(stream_value, str) and str is not bytes:
                    raise Exception('bad stream_value')
                self.input_streams.setdefault(stream_type, []).append(
                    stream_value)
        self.here = here
        self.unparsed_opts = options
        self.outputs = []
        # Could take parsed args, but for now this is easier.
        self.unparsed_args = args
        self.proc_outputs = list(proc_outputs)
        self.require_proc_stdout = False
        self.proc_results = list(proc_results)

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
        for stream_value in streams:
            if getattr(stream_value, 'read', None):
                yield stream_value
            else:
                yield BytesIO(stream_value)

    def make_result(self, get_id, test_command, previous_run=None):
        result = TestResultModel(self, get_id, previous_run)
        return result, result._summary

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

    def output_summary(self, successful, tests, tests_delta, time, time_delta, values):
        self.outputs.append(
            ('summary', successful, tests, tests_delta, time, time_delta, values))

    def subprocess_Popen(self, *args, **kwargs):
        # Really not an output - outputs should be renamed to events.
        self.outputs.append(('popen', args, kwargs))
        result = ProcessModel(self)
        if self.proc_outputs:
            result.stdout = BytesIO(self.proc_outputs.pop(0))
        elif self.require_proc_stdout:
            raise Exception("No process output available")
        if self.proc_results:
            result.returncode = self.proc_results.pop(0)
        return result
