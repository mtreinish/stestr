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

"""Run a projects tests and load them into testrepository."""

import ConfigParser
from cStringIO import StringIO
import optparse
import os.path
import string

from testtools import TestResult

from testrepository.arguments.string import StringArgument
from testrepository.commands import Command
from testrepository.testcommand import TestCommand, testrconf_help

class run(Command):
    __doc__ = """Run the tests for a project and load them into testrepository.
    """ + testrconf_help

    options = [optparse.Option("--failing", action="store_true",
            default=False, help="Run only tests known to be failing.")]
    args = [StringArgument('testargs', 0, None)]
    # Can be assigned to to inject a custom command factory.
    command_factory = TestCommand

    def run(self):
        testcommand = self.command_factory(self.ui)
        if self.ui.options.failing:
            # Run only failing tests
            repo = self.repository_factory.open(self.ui.here)
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
        if self.ui.options.quiet:
            quiet = "-q "
        else:
            quiet = ""
        load_cmd = '| testr load %s-d %s' % (quiet, self.ui.here)
        cmd = testcommand.get_run_command(ids, self.ui.arguments['testargs'])
        cmd.setUp()
        try:
            command = cmd.cmd + load_cmd
            self.ui.output_values([('running', command)])
            proc = self.ui.subprocess_Popen(command, shell=True)
            proc.communicate()
            return proc.returncode
        finally:
            cmd.cleanUp()
        template = string.Template(
            ' '.join(elements) + '| testr load %s-d %s' % (quiet, self.ui.here))
