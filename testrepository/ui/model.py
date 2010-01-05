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

class UI(ui.AbstractUI):
    """A object based UI.
    
    This is useful for reusing the Command objects that provide a simplified
    interaction model with the domain logic from python. It is used for
    testing testrepository commands.
    """

    def __init__(self, input_streams=None, options=()):
        """Create a model UI.

        :param input_streams: A list of stream name, bytes stream tuples to be
            used as the available input streams for this ui.
        :param options: Options to explicitly set values for.
        """
        self.input_streams = {}
        if input_streams:
            for stream_type, stream_bytes in input_streams:
                self.input_streams.setdefault(stream_type, []).append(
                    stream_bytes)
        self.here = 'memory:'
        self.options = optparse.Values()
        seen_options = set()
        for option, value in options:
            setattr(self.options, option, value)
            seen_options.add(option)
        if not 'quiet' in seen_options:
            setattr(self.options, 'quiet', False)
        self.outputs = []

    def _iter_streams(self, stream_type):
        streams = self.input_streams.pop(stream_type, [])
        for stream_bytes in streams:
            yield StringIO(stream_bytes)

    def output_values(self, values):
        self.outputs.append(values)
