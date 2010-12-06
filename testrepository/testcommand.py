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

"""The test command that test repository knows how to run."""

import ConfigParser
from fixtures import Fixture
import os.path
import re
import string
import subprocess
import tempfile
from textwrap import dedent

testrconf_help = dedent("""
    Configuring via .testr.conf:
    ---
    [DEFAULT]
    test_command=foo $IDOPTION
    test_id_option=--bar $IDFILE
    ---
    will cause 'testr run' to run 'foo | testr load', and 'testr run --failing'
    to run 'foo --bar failing.list | testr load'.

    The full list of options and variables for .testr.conf:
    * test_command -- command line to run to execute tests.
    * test_id_option -- the value to substitute into test_command when specific
      test ids should be run.
    * test_id_list_default -- the value to use for $IDLIST when no specific
      test ids are being run.
    * $IDOPTION -- the variable to use to trigger running some specific tests.
    * $IDFILE -- A file created before the test command is run and deleted
      afterwards which contains a list of test ids, one per line. This can
      handle test ids with emedded whitespace.
    * $IDLIST -- A list of the test ids to run, separated by spaces. IDLIST
      defaults to an empty string when no test ids are known and no explicit
      default is provided. This will not handle test ids with spaces.
    """)


class TestListingFixture(Fixture):
    """Write a temporary file to disk with test ids in it."""

    def __init__(self, test_ids, cmd_template, ui, listpath=None):
        """Create a TestListingFixture.

        :param test_ids: The test_ids to use. May be None indicating that
            no ids are present.
        :param cmd_template: string to be filled out with
            IDFILE.
        :param ui: The UI in use.
        :param listpath: The file listing path to use. If None, a unique path
            is created.
        """
        self.test_ids = test_ids
        self.template = cmd_template
        self.ui = ui
        self._listpath = listpath

    def setUp(self):
        super(TestListingFixture, self).setUp()
        if self.test_ids is None:
            self.list_file_name = None
            name = ''
            self.test_ids = []
        else:
            name = self.make_listfile()
        cmd = self.template
        cmd = re.sub('\$IDFILE', name, cmd)
        idlist = ' '.join(self.test_ids)
        cmd = re.sub('\$IDLIST', idlist, cmd)
        self.cmd = cmd

    def make_listfile(self):
        name = None
        try:
            if self._listpath:
                name = self._listpath
                stream = open(name, 'wb')
            else:
                fd, name = tempfile.mkstemp()
                stream = os.fdopen(fd, 'wb')
            self.list_file_name = name
            stream.write('\n'.join(list(self.test_ids) + ['']))
            stream.close()
        except:
            if name:
                os.unlink(name)
            raise
        self.addCleanup(os.unlink, name)
        return name

    def run_tests(self):
        """Run the tests defined by the command and ui.

        :return: A list of spawned processes.
        """
        self.ui.output_values([('running', self.cmd)])
        run_proc = self.ui.subprocess_Popen(self.cmd, shell=True,
            stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        # Prevent processes stalling if they read from stdin; we could
        # pass this through in future, but there is no point doing that
        # until we have a working can-run-debugger-inline story.
        run_proc.stdin.close()
        return [run_proc]


class TestCommand(object):
    """Represents the test command defined in .testr.conf.
    
    :ivar run_factory: The fixture to use to execute a command.
    :ivar oldschool: Use failing.list rather than a unique file path.
    """
    
    run_factory = TestListingFixture
    oldschool = False

    def __init__(self, ui):
        """Create a TestCommand.

        :param ui: A testrepository.ui.UI object which is used to obtain the
            location of the .testr.conf.
        """
        self.ui = ui

    def get_run_command(self, test_ids=None, testargs=()):
        """Get the command that would be run to run tests."""
        parser = ConfigParser.ConfigParser()
        if not parser.read(os.path.join(self.ui.here, '.testr.conf')):
            raise ValueError("No .testr.conf config file")
        try:
            command = parser.get('DEFAULT', 'test_command')
        except ConfigParser.NoOptionError, e:
            if e.message != "No option 'test_command' in section: 'DEFAULT'":
                raise
            raise ValueError("No test_command option present in .testr.conf")
        elements = [command] + list(testargs)
        cmd = ' '.join(elements)
        if test_ids is None:
            try:
                idlist = parser.get('DEFAULT', 'test_id_list_default')
                test_ids = idlist.split()
            except ConfigParser.NoOptionError, e:
                if e.message != "No option 'test_id_list_default' in section: 'DEFAULT'":
                    raise
                test_ids = None
        if '$IDOPTION' in command:
            # IDOPTION is used, we must have it configured.
            try:
                idoption = parser.get('DEFAULT', 'test_id_option')
            except ConfigParser.NoOptionError, e:
                if e.message != "No option 'test_id_option' in section: 'DEFAULT'":
                    raise
                raise ValueError("No test_id_option option present in .testr.conf")
            if test_ids is None:
                # No test ids, no id option.
                idoption = ''
            cmd = re.sub('\$IDOPTION', idoption, cmd)
        if self.oldschool:
            listpath = os.path.join(self.ui.here, 'failing.list')
            result = self.run_factory(test_ids, cmd, self.ui, listpath)
        else:
            result = self.run_factory(test_ids, cmd, self.ui)
        return result
