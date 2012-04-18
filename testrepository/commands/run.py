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

import optparse

from testtools import TestResult

from testrepository.arguments.string import StringArgument
from testrepository.commands import Command
from testrepository.commands.load import load
from testrepository.ui import decorator
from testrepository.testcommand import TestCommand, testrconf_help


class run(Command):
    __doc__ = """Run the tests for a project and load them into testrepository.
    """ + testrconf_help

    options = [
        optparse.Option("--failing", action="store_true",
            default=False, help="Run only tests known to be failing."),
        optparse.Option("--parallel", action="store_true",
            default=False, help="Run tests in parallel processes."),
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
        cmd = testcommand.get_run_command(ids, self.ui.arguments['testargs'])
        cmd.setUp()
        try:
            run_procs = [('subunit', proc.stdout) for proc in cmd.run_tests()]
            options = {}
            if self.ui.options.failing:
                options['partial'] = True
            load_ui = decorator.UI(input_streams=run_procs, options=options,
                decorated=self.ui)
            load_cmd = load(load_ui)
            return load_cmd.execute()
        finally:
            cmd.cleanUp()
