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

"""'Commands' for testr.

The code in this module contains the Command base class, the run_argv
entry point to run CLI commands.

Actual commands can be found in testrepository.commands.$commandname.

For example, testrepository.commands.init is the init command name, and 
testrepository.command.show_stats would be the show-stats command (if one
existed). The Command discovery logic looks for a class in the module with
the same name - e.g. tesrepository.commands.init.init would be the class.
That class must obey the testrepository.commands.Command protocol, but does
not need to be a subclass.

Plugins and extensions wanting to add commands should install them into
testrepository.commands (perhaps by extending the testrepository.commands
__path__ to include a directory containing their commands - no __init__ is
needed in that directory.)
"""

def _find_command(cmd_name):
    classname = "%s" % cmd_name
    modname = "testrepository.commands.%s" % cmd_name
    try:
        _temp = __import__(modname, globals(), locals(), [classname])
    except ImportError:
        raise KeyError("Could not import command module %s" % modname)
    result = getattr(_temp, classname, None)
    if result is None:
        raise KeyError(
            "Malformed command module - no command class %s found in module %s."
            % (classname, modname))
    return result


class Command(object):
    """A command that can be run.

    Commands contain non-UI non-domain specific behaviour - they are the
    glue between the UI and the object model.

    Commands are parameterised with a UI object which is responsible for
    brokering the command arguments, input and output.
    """

    def __init__(self, ui):
        """Create a Command object with ui ui."""


def run_argv(argv, stdin, stdout, stderr):
    """Convenience function to run a command with a CLIUI.

    :param argv: The argv to run the command with.
    :param stdin: The stdin stream for the command.
    :param stdout: The stdout stream for the command.
    :param stderr: The stderr stream for the command.
    :return: An integer exit code for the command.
    """
    cmd = _find_command(argv[1])
