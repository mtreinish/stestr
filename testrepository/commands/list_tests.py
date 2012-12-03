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

"""List the tests from a project and show them."""

from cStringIO import StringIO

from testtools import TestResult

from testrepository.arguments.doubledash import DoubledashArgument
from testrepository.arguments.string import StringArgument
from testrepository.commands import Command
from testrepository.testcommand import testrconf_help, TestCommand


class list_tests(Command):
    __doc__ = """Lists the tests for a project.
    """ + testrconf_help

    args = [StringArgument('testfilters', 0, None), DoubledashArgument(),
        StringArgument('testargs', 0, None)]
    # Can be assigned to to inject a custom command factory.
    command_factory = TestCommand

    def run(self):
        testcommand = self.command_factory(self.ui, None)
        ids = None
        filters = None
        if self.ui.arguments['testfilters']:
            filters = self.ui.arguments['testfilters']
        cmd = testcommand.get_run_command(ids, self.ui.arguments['testargs'],
            test_filters=filters)
        cmd.setUp()
        try:
            # Ugh.
            # List tests if the fixture has not already needed to to filter.
            if filters is None:
                ids = cmd.list_tests()
            else:
                ids = cmd.test_ids
            stream = StringIO()
            for id in ids:
                stream.write('%s\n' % id)
            stream.seek(0)
            self.ui.output_stream(stream)
            return 0
        finally:
            cmd.cleanUp()
