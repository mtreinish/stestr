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

from testrepository import ui

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
