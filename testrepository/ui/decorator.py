#
# Copyright (c) 2010 Testrepository Contributors
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

"""A decorator for UIs to allow use of additional command objects in-process."""

from StringIO import StringIO
import optparse

from testrepository import ui


class UI(ui.AbstractUI):
    """A decorating UI.
    
    Not comprehensive yet - only supports overriding input streams. Note that
    because UI objects carry command specific state only specific things can
    be delegated - option/argument lookup, streams. set_command for instance, 
    does not get passed to the decorated UI unless it has not been initialised.
    """

    def __init__(self, input_streams=None, options={}, decorated=None):
        """Create a decorating UI.
        
        :param input_streams: The input steams to present from this UI. Should
            be a list of (stream name, file) tuples.
        :param options: Dict of options to replace in the base UI. These are
            merged with the underlying ones when set_command is called.
        :param decorated: The UI to decorate.
        """
        self._decorated = decorated
        self.input_streams = {}
        if input_streams:
            for stream_type, stream_value in input_streams:
                self.input_streams.setdefault(stream_type, []).append(
                    stream_value)
        self._options = options

    @property
    def arguments(self):
        return self._decorated.arguments

    @property
    def here(self):
        return self._decorated.here

    def _iter_streams(self, stream_type):
        streams = self.input_streams.pop(stream_type, [])
        for stream_value in streams:
            if getattr(stream_value, 'read', None):
                yield stream_value
            else:
                yield StringIO(stream_value)

    def make_result(self, get_id, previous_run=None):
        return self._decorated.make_result(get_id, previous_run)

    def output_error(self, error_tuple):
        return self._decorated.output_error(error_tuple)

    def output_rest(self, rest_string):
        return self._decorated.output_rest(rest_string)

    def output_stream(self, stream):
        return self._decorated.output_stream(stream)

    def output_table(self, table):
        return self._decorated.output_table(table)

    def output_tests(self, tests):
        return self._decorated.output_tests(tests)

    def output_values(self, values):
        return self._decorated.output_values(values)

    def output_summary(self, successful, tests, tests_delta, time, time_delta, values):
        return self._decorated.output_summary(
            successful, tests, tests_delta, time, time_delta, values)

    def set_command(self, cmd):
        self.cmd = cmd
        result = True
        if getattr(self._decorated, 'cmd', None) is None:
            result = self._decorated.set_command(cmd)
        # Pickup the repository factory from the decorated UI's command.
        cmd.repository_factory = self._decorated.cmd.repository_factory
        # Merge options
        self.options = optparse.Values()
        for option in dir(self._decorated.options):
            setattr(self.options, option,
                getattr(self._decorated.options, option))
        for option, value in self._options.items():
            setattr(self.options, option, value)
        return result

    def subprocess_Popen(self, *args, **kwargs):
        return self._decorated.subprocess_Popen(*args, **kwargs)
