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

import os

import subunit

from testrepository.repository import file

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
    if getattr(result, 'name', None) is None:
        # Store the name for the common case of name == lookup path.
        result.name = classname
    return result


def iter_commands():
    """Iterate over all the command classes."""
    paths = __path__
    names = set()
    for path in paths:
        # For now, only support regular installs. TODO: support zip, eggs.
        for filename in os.listdir(path):
            base = os.path.basename(filename)
            if base.startswith('.'):
                continue
            name = base.split('.', 1)[0]
            names.add(name)
    names.discard('__init__')
    names = sorted(names)
    for name in names:
        yield _find_command(name)


class Command(object):
    """A command that can be run.

    Commands contain non-UI non-domain specific behaviour - they are the
    glue between the UI and the object model.

    Commands are parameterised with:
    :ivar ui: a UI object which is responsible for brokering the command
        arguments, input and output. There is no default ui, it must be
        passed to the constructor.
    
    :ivar repository_factory: a repository factory which is used to create or
        open repositories. The default repository factory is suitable for
        use in the command line tool.

    Commands declare that they accept/need/emit:
    :ivar args: A list of testrepository.arguments.AbstractArgument instances.
        AbstractArgument arguments are validated when set_command is called on
        the UI layer.
    :ivar input_streams: A list of stream specifications. Mandatory streams
        are specified by a simple name. Optional streams are specified by
        a simple name with a ? ending the name. Optional multiple streams are
        specified by a simple name with a * ending the name, and mandatory
        multiple streams by ending the name with +. Multiple streams are used
        when a command can process more than one stream.
    :ivar options: A list of optparse.Option options to accept. These are
        merged with global options by the UI layer when set_command is called.
    """

    # class defaults to no streams.
    input_streams = []
    # class defaults to no arguments.
    args = []
    # class defaults to no options.
    options = []

    def __init__(self, ui):
        """Create a Command object with ui ui."""
        self.ui = ui
        self.repository_factory = file.RepositoryFactory()
        self._init()

    def execute(self):
        """Execute a command.

        This interrogates the UI to ensure that arguments and options are
        supplied, performs any validation for the same that the command needs
        and finally calls run() to perform the command. Most commands should
        not need to override this method, and any user wanting to run a 
        command should call this method.
        """
        if not self.ui.set_command(self):
            return 1
        result = self.run()
        if not result:
            return 0
        return result

    @classmethod
    def get_summary(klass):
        docs = klass.__doc__.split('\n')
        return docs[0]

    def _init(self):
        """Per command init call, called into by Command.__init__."""

    def output_run(self, run_id, output, evaluator):
        """Output a test run.

        :param run_id: The run id.
        :param output: A StringIO containing a subunit stream for some portion of the run to show.
        :param evaluator: A TestResult evaluating the entire run.
        """
        if self.ui.options.quiet:
            return
        if output.getvalue():
            output.seek(0)
            self.ui.output_results(subunit.ProtocolTestCase(output))
        values = [('id', run_id), ('tests', evaluator.testsRun)]
        failures = len(evaluator.failures) + len(evaluator.errors)
        if failures:
            values.append(('failures', failures))
        skips = sum(map(len, evaluator.skip_reasons.itervalues()))
        if skips:
            values.append(('skips', skips))
        self.ui.output_values(values)

    def run(self):
        """The core logic for this command to be implemented by subclasses."""
        raise NotImplementedError(self.run)


def run_argv(argv, stdin, stdout, stderr):
    """Convenience function to run a command with a CLIUI.

    :param argv: The argv to run the command with.
    :param stdin: The stdin stream for the command.
    :param stdout: The stdout stream for the command.
    :param stderr: The stderr stream for the command.
    :return: An integer exit code for the command.
    """
    cmd_name = None
    cmd_args = argv[1:]
    for arg in argv[1:]:
        if not arg.startswith('-'):
            cmd_name = arg
            break
    if cmd_name is None:
        cmd_name = 'help'
        cmd_args = ['help']
    cmd_args.remove(cmd_name)
    cmdclass = _find_command(cmd_name)
    from testrepository.ui import cli
    ui = cli.UI(cmd_args, stdin, stdout, stderr)
    cmd = cmdclass(ui)
    result = cmd.execute()
    if not result:
        return 0
    return result
