#
# Copyright (c) 2010-2012 Testrepository Contributors
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

"""Run a projects tests and load them into testrepository."""

from cStringIO import StringIO
import optparse

from testtools import TestResult

from testrepository.arguments.string import StringArgument
from testrepository.commands import Command
from testrepository.commands.load import load
from testrepository.ui import decorator
from testrepository.testcommand import TestCommand, testrconf_help
from testrepository.testlist import parse_list


class ReturnCodeToSubunit(object):
    """Converts a process return code to a subunit error on the process stdout.

    The ReturnCodeToSubunit object behaves as a readonly stream, supplying
    the read, readline and readlines methods. If the process exits non-zero a
    synthetic test is added to the output, making the error accessible to
    subunit stream consumers. If the process closes its stdout and then does
    not terminate, reading from the ReturnCodeToSubunit stream will hang.
    """

    def __init__(self, process):
        """Adapt a process to a readable stream.

        :param process: A subprocess.Popen object that is
            generating subunit.
        """
        self.proc = process
        self.done = False
        self.source = self.proc.stdout
        self.lastoutput = '\n'

    def _append_return_code_as_test(self):
        if self.done is True:
            return
        self.source = StringIO()
        returncode = self.proc.wait()
        if returncode != 0:
            if self.lastoutput != '\n':
                # Subunit is line orientated, it has to start on a fresh line.
                self.source.write('\n')
            self.source.write('test: process-returncode\n'
                'error: process-returncode [\n'
                ' returncode %d\n'
                ']\n' % returncode)
        self.source.seek(0)
        self.done = True

    def read(self, count=-1):
        if count == 0:
            return ''
        result = self.source.read(count)
        if result:
            self.lastoutput = result[-1]
            return result
        self._append_return_code_as_test()
        return self.source.read(count)

    def readline(self):
        result = self.source.readline()
        if result:
            self.lastoutput = result[-1]
            return result
        self._append_return_code_as_test()
        return self.source.readline()

    def readlines(self):
        result = self.source.readlines()
        if result:
            self.lastoutput = result[-1][-1]
        self._append_return_code_as_test()
        result.extend(self.source.readlines())
        return result


class run(Command):
    __doc__ = """Run the tests for a project and load them into testrepository.
    """ + testrconf_help

    options = [
        optparse.Option("--failing", action="store_true",
            default=False, help="Run only tests known to be failing."),
        optparse.Option("--parallel", action="store_true",
            default=False, help="Run tests in parallel processes."),
        optparse.Option("--concurrency", action="store", type="int", default=0,
            help="How many processes to use. The default (0) autodetects your CPU count."),
        optparse.Option("--load-list", default=None,
            help="Only run tests listed in the named file."),
        optparse.Option("--partial", action="store_true",
            default=False,
            help="Only some tests will be run. Implied by --failing."),
        optparse.Option("--subunit", action="store_true",
            default=False, help="Display results in subunit format."),
        optparse.Option("--full-results", action="store_true",
            default=False,
            help="Show all test results. Currently only works with --subunit."),
        ]
    args = [StringArgument('testargs', 0, None)]
    # Can be assigned to to inject a custom command factory.
    command_factory = TestCommand

    def run(self):
        repo = self.repository_factory.open(self.ui.here)
        testcommand = self.command_factory(self.ui, repo)
        if self.ui.options.failing:
            # Run only failing tests
            run = repo.get_failing()
            case = run.get_test()
            result = TestResult()
            result.startTestRun()
            try:
                case.run(result)
            finally:
                result.stopTestRun()
            ids = [failure[0].id() for failure in result.failures]
            ids.extend([error[0].id() for error in result.errors])
        else:
            ids = None
        if self.ui.options.load_list:
            list_ids = set()
            with file(self.ui.options.load_list) as list_file:
                list_ids = set(parse_list(list_file.read()))
            if ids is None:
                # Use the supplied list verbatim
                ids = list_ids
            else:
                # We have some already limited set of ids, just reduce to ids
                # that are both failing and listed.
                ids = list_ids.intersection(ids)
        cmd = testcommand.get_run_command(ids, self.ui.arguments['testargs'])
        cmd.setUp()
        try:
            run_procs = [('subunit', ReturnCodeToSubunit(proc)) for proc in cmd.run_tests()]
            options = {}
            if self.ui.options.failing:
                options['partial'] = True
            load_ui = decorator.UI(input_streams=run_procs, options=options,
                decorated=self.ui)
            load_cmd = load(load_ui)
            return load_cmd.execute()
        finally:
            cmd.cleanUp()
