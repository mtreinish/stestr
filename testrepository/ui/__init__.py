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

"""In testrepository a UI is an interface to a 'user' (which may be a machine).

The testrepository.ui.cli module contains a command line interface, and the
module testrepository.ui.model contains a purely object based implementation
which is used for testing testrepository.

See AbstractUI for details on what UI classes should do and are responsible
for.
"""

class AbstractUI(object):
    """The base class for UI objects, this providers helpers and the interface.

    A UI object is responsible for brokering interactions with a particular
    user environment (e.g. the command line). These interactions can take
    several forms:
     - reading bulk data
     - gathering data
     - emitting progress or activity data - hints as to the programs execution.
     - providing notices about actions taken
     - showing the result of some query (including errors)
    All of these things are done in a structured fashion. See the methods
    iter_streams, query_user, progress, notice and result.

    UI objects are generally expected to be used once, with a fresh one
    created for each command executed.

    :ivar cmd: The command that is running using this UI object.
    :ivar here: The location that command is being run in. This may be a local
        path or a URL. This is only guaranteed to be set after set_command is
        called, as some UI's need to do option processing to determine its
        value.
    :ivar options: The options for this ui, containing both global and command
        specific options.
    """

    def iter_streams(self, stream_type):
        """Iterate over all the streams of type stream_type.

        Implementors of UI should implement _iter_streams which is called after
        argument checking is performed.

        :param stream_type: A simple string such as 'subunit' which matches
            one of the stream types defined for the cmd object this UI is
            being used with.
        :return: A generator of stream objects. stream objects have a read
            method and a close method which behave as for file objects.
        """
        for stream_spec in self.cmd.input_streams:
            if '*' in stream_spec or '?' in stream_spec or '+' in stream_spec:
                found = stream_type == stream_spec[:-1]
            else:
                found = stream_type == stream_spec
            if found:
                return self._iter_streams(stream_type)
        raise KeyError(stream_type)

    def _iter_streams(self, stream_type):
        """Helper for iter_streams which subclasses should implement."""
        raise NotImplementedError(self._iter_streams)

    def output_results(self, suite_or_test):
        """Show suite_or_test to the user by 'running' it.

        This expects the run to be fast/cheap.

        :param suite_or_test: A suite or test to show to the user. This should
            obey the 'TestCase' protocol - it should have a method run(result)
            that causes all the tests contained in the object to be handed to
            the result object.
        """
        raise NotImplementedError(self.output_results)

    def output_table(self, table):
        """Show a table to the user.

        :param table: an iterable of rows. The first row is used for column
            headings, and every row needs the same number of cells.
            e.g. output_table([('name', 'age'), ('robert', 1234)])
        """
        raise NotImplementedError(self.output_table)

    def output_values(self, values):
        """Show values to the user.

        :param values: An iterable of (label, value).
        """
        raise NotImplementedError(self.output_values)

    def set_command(self, cmd):
        """Inform the UI what command it is running.

        This is used to gather command line arguments, or prepare dialogs and
        otherwise ensure that the information the command has declared it needs
        will be available. The default implementation simply sets self.cmd to
        cmd.
        
        :param cmd: A testrepository.commands.Command.
        """
        self.cmd = cmd
