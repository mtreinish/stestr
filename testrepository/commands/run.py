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

class run(Command):
    """Run the tests for a project and load them into testrepository.
    
    This reads the commands to run from .testr.conf. Setting that file to
    ---
    [DEFAULT]
    test_command=foo $IDOPTION
    test_id_option=--bar $IDFILE
    ---
    will cause 'testr run' to run 'foo | testr load', and 'testr run --failing'
    to run 'foo --bar failing.list | testr load'.
    """

    options = [optparse.Option("--failing", action="store_true",
            default=False, help="Run only tests known to be failing.")]
    args = [StringArgument('testargs', 0, None)]

    def run(self):
        parser = ConfigParser.ConfigParser()
        if not parser.read(os.path.join(self.ui.here, '.testr.conf')):
            raise ValueError("No .testr.conf config file")
        try:
            command = parser.get('DEFAULT', 'test_command')
        except ConfigParser.NoOptionError, e:
            if e.message != "No option 'test_command' in section: 'DEFAULT'":
                raise
            raise ValueError("No test_command option present in .testr.conf")
        elements = [command]
        elements.extend(self.ui.arguments['testargs'])
        template = string.Template(' '.join(elements) + '| testr load')
        if self.ui.options.failing:
            # Run only failing tests
            try:
                idoption = parser.get('DEFAULT', 'test_id_option')
            except ConfigParser.NoOptionError, e:
                if e.message != "No option 'test_id_option' in section: 'DEFAULT'":
                    raise
                raise ValueError("No test_id_option option present in .testr.conf")
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
            idfilename = os.path.join(self.ui.here, 'failing.list')
            idoption = string.Template(idoption).substitute(IDFILE=idfilename)
            idfile = file(idfilename, 'wt')
            try:
                for id in ids:
                    idfile.write('%s\n' % id)
            finally:
                idfile.close()
        else:
            # Run all
            idoption = ''
            idfilename = ''
        try:
            command = template.substitute(IDOPTION=idoption, IDFILE=idfilename)
            self.ui.output_values([('running', command)])
            proc = self.ui.subprocess_Popen(command, shell=True)
            proc.communicate()
            return proc.returncode
        finally:
            if idfilename:
                os.unlink(idfilename)
