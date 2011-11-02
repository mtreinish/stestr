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

from testtools import TestResult

from testrepository.utils import timedelta_to_seconds


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
    :ivar options: The parsed options for this ui, containing both global and
        command specific options.
    :ivar arguments: The parsed arguments for this ui. Set Command.args to
        define the accepted arguments for a command.
    """

    def _check_cmd(self):
        """Check that cmd is valid. This method is meant to be overridden.
        
        :return: True if the cmd is valid - if options and args match up with
            the ones supplied to the UI, and so on.
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

    def make_result(self, get_id, previous_run=None):
        """Make a `TestResult` that can be used to display test results.

        :param get_id: A nullary callable that returns the id of the test run
            when called.
        :param previous_run: An optional previous test run.
        """
        raise NotImplementedError(self.make_result)

    def output_error(self, error_tuple):
        """Show an error to the user.

        This is typically used only by Command.execute when run raises an
        exception.

        :param error_tuple: An error tuple obtained from sys.exc_info().
        """
        raise NotImplementedError(self.output_error)

    def output_rest(self, rest_string):
        """Show rest_string - a ReST document.

        This is typically used as the entire output for command help or
        documentation.
        
        :param rest_string: A ReST source to display.
        """
        raise NotImplementedError(self.output_rest)

    def output_stream(self, stream):
        """Show a byte stream to the user.

        This is not currently typed, but in future a MIME type may be
        permitted.

        :param stream: A file like object that can be read from. The UI will
        not close the file.
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

    def output_summary(self, successful, tests, tests_delta, time, time_delta, values):
        """Output a summary of a test run.

        An example summary might look like:
          Run 565 (+2) tests in 2.968s
          FAILED (errors=13 (-2), succeesses=31 (+2))

        :param successful: A boolean indicating whether the result was
            successful.
        :param values: A dict mapping from name (e.g. "successes") to a tuple
            of ``(value, delta)``. e.g. (31, -2)

        """
        raise NotImplementedError(self.output_summary)

    def set_command(self, cmd):
        """Inform the UI what command it is running.

        This is used to gather command line arguments, or prepare dialogs and
        otherwise ensure that the information the command has declared it needs
        will be available. The default implementation simply sets self.cmd to
        cmd.
        
        :param cmd: A testrepository.commands.Command.
        """
        self.cmd = cmd
        return self._check_cmd()

    def subprocess_Popen(self, *args, **kwargs):
        """Call an external process from the UI's context.
        
        The behaviour of this call should match the Popen process on any given
        platform, except that the UI can take care of any wrapping or
        manipulation needed to fit into its environment.
        """
        # This might not be the right place.
        raise NotImplementedError(self.subprocess_Popen)


class BaseUITestResult(TestResult):
    """An abstract test result used with the UI.

    AbstractUI.make_result probably wants to return an object like this.
    """

    def __init__(self, ui, get_id):
        """Construct an `AbstractUITestResult`.

        :param ui: The UI this result is associated with.
        :param get_id: A nullary callable that returns the id of the test run.
        """
        super(BaseUITestResult, self).__init__()
        self.ui = ui
        self.get_id = get_id

    def startTestRun(self):
        super(BaseUITestResult, self).startTestRun()
        self._start_time = None

    def time(self, a_time):
        if self._start_time is None:
            self._start_time = a_time
        super(BaseUITestResult, self).time(a_time)

    def _output_summary(self, run_id):
        """Output a test run.

        :param run_id: The run id.
        """
        # XXX: Feed deltas into output_summary, means getting last test run.
        #  - failures
        #  - tests
        #  - time
        if self.ui.options.quiet:
            return
        now = self._now()
        if now and self._start_time:
            time = timedelta_to_seconds(now - self._start_time)
        else:
            time = None
        values = [('id', run_id, None)]
        failures = len(self.failures) + len(self.errors)
        if failures:
            values.append(('failures', failures, None))
        skips = sum(map(len, self.skip_reasons.itervalues()))
        if skips:
            values.append(('skips', skips, None))
        self.ui.output_summary(not bool(failures), self.testsRun, None, time, None, values)

    def stopTestRun(self):
        super(BaseUITestResult, self).stopTestRun()
        run_id = self.get_id()
        self._output_summary(run_id)
