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

from extras import (
    try_import,
    try_imports,
    )

from collections import defaultdict
ConfigParser = try_imports(['ConfigParser', 'configparser'])
import io
import itertools
import operator
import os.path
import re
import subprocess
import sys
import tempfile
import multiprocessing
from textwrap import dedent

import fixtures
v2 = try_import('subunit.v2')

from stestr.fixtures import test_listing
from stestr import results
from stestr.testlist import (
    parse_enumeration,
    write_list,
    )

testrconf_help = dedent("""
    Configuring via .testr.conf:
    ---
    [DEFAULT]
    test_command=foo $IDOPTION
    test_id_option=--bar $IDFILE
    ---
    will cause 'testr run' to run 'foo' to execute tests, and
    'testr run --failing' will cause 'foo --bar failing.list ' to be run to
    execute tests. Shell variables are expanded in these commands on platforms
    that have a shell.

    The full list of options and variables for .testr.conf:
    * filter_tags -- a list of tags which should be used to filter test counts.
      This is useful for stripping out non-test results from the subunit stream
      such as Zope test layers. These filtered items are still considered for
      test failures.
    * test_command -- command line to run to execute tests.
    * test_id_option -- the value to substitute into test_command when specific
      test ids should be run.
    * test_id_list_default -- the value to use for $IDLIST when no specific
      test ids are being run.
    * test_list_option -- the option to use to cause the test runner to report
      on the tests it would run, rather than running them. When supplied the
      test_command should output on stdout all the test ids that would have
      been run if every other option and argument was honoured, one per line.
      This is required for parallel testing, and is substituted into $LISTOPT.
    * test_run_concurrency -- Optional call out to establish concurrency.
      Should return one line containing the number of concurrent test runner
      processes to run.
    * instance_provision -- provision one or more test run environments.
      Accepts $INSTANCE_COUNT for the number of instances desired.
    * instance_execute -- execute a test runner process in a given environment.
      Accepts $INSTANCE_ID, $FILES and $COMMAND. Paths in $FILES should be
      synchronised into the test runner environment filesystem. $COMMAND can
      be adjusted if the paths are synched with different names.
    * instance_dispose -- dispose of one or more test running environments.
      Accepts $INSTANCE_IDS.
    * group_regex -- If set group tests by the matched section of the test id.
    * $IDOPTION -- the variable to use to trigger running some specific tests.
    * $IDFILE -- A file created before the test command is run and deleted
      afterwards which contains a list of test ids, one per line. This can
      handle test ids with emedded whitespace.
    * $IDLIST -- A list of the test ids to run, separated by spaces. IDLIST
      defaults to an empty string when no test ids are known and no explicit
      default is provided. This will not handle test ids with spaces.

    See the stestr manual for example .testr.conf files in different
    programming languages.

    """)


class CallWhenProcFinishes(object):
    """Convert a process object to trigger a callback when returncode is set.
    
    This just wraps the entire object and when the returncode attribute access
    finds a set value, calls the callback.
    """

    def __init__(self, process, callback):
        """Adapt process

        :param process: A subprocess.Popen object.
        :param callback: The process to call when the process completes.
        """
        self._proc = process
        self._callback = callback
        self._done = False

    @property
    def stdin(self):
        return self._proc.stdin

    @property
    def stdout(self):
        return self._proc.stdout

    @property
    def stderr(self):
        return self._proc.stderr

    @property
    def returncode(self):
        result = self._proc.returncode
        if not self._done and result is not None:
            self._done = True
            self._callback()
        return result

    def wait(self):
        return self._proc.wait()


compiled_re_type = type(re.compile(''))


class TestCommand(fixtures.Fixture):
    """Represents the test command defined in .testr.conf.
    
    :ivar run_factory: The fixture to use to execute a command.
    :ivar oldschool: Use failing.list rather than a unique file path.

    TestCommand is a Fixture. Many uses of it will not require it to be setUp,
    but calling get_run_command does require it: the fixture state is used to
    track test environment instances, which are disposed of when cleanUp
    happens. This is not done per-run-command, because test bisection (amongst
    other things) uses multiple get_run_command configurations.
    """
    
    run_factory = test_listing.TestListingFixture
    oldschool = False

    def __init__(self, ui, repository):
        """Create a TestCommand.

        :param ui: A stestr.ui.UI object which is used to obtain the
            location of the .testr.conf.
        :param repository: A stestr.repository.Repository used for
            determining test times when partitioning tests.
        """
        super(TestCommand, self).__init__()
        self.ui = ui
        self.repository = repository
        self._instances = None
        self._allocated_instances = None

    def setUp(self):
        super(TestCommand, self).setUp()
        self._instances = set()
        self._allocated_instances = set()
        self.addCleanup(self._dispose_instances)

    def _dispose_instances(self):
        instances = self._instances
        if instances is None:
            return
        self._instances = None
        self._allocated_instances = None
        try:
            dispose_cmd = self.get_parser().get('DEFAULT', 'instance_dispose')
        except (ValueError, ConfigParser.NoOptionError):
            return
        variable_regex = '\$INSTANCE_IDS'
        dispose_cmd = re.sub(variable_regex, ' '.join(sorted(instance.decode('utf') for instance in instances)),
            dispose_cmd)
        self.ui.output_values([('running', dispose_cmd)])
        run_proc = self.ui.subprocess_Popen(dispose_cmd, shell=True)
        run_proc.communicate()
        if run_proc.returncode:
            raise ValueError('Disposing of instances failed, return %d' %
                run_proc.returncode)

    def get_parser(self):
        """Get a parser with the .testr.conf in it."""
        parser = ConfigParser.ConfigParser()
        # This possibly should push down into UI.
        if self.ui.here == 'memory:':
            return parser
        if not parser.read(os.path.join(self.ui.here, '.testr.conf')):
            raise ValueError("No .testr.conf config file")
        return parser

    def get_run_command(self, test_ids=None, testargs=(), test_filters=None):
        """Get the command that would be run to run tests.
        
        See TestListingFixture for the definition of test_ids and test_filters.
        """
        if self._instances is None:
            raise TypeError('TestCommand not setUp')
        parser = self.get_parser()
        try:
            command = parser.get('DEFAULT', 'test_command')
        except ConfigParser.NoOptionError as e:
            if e.message != "No option 'test_command' in section: 'DEFAULT'":
                raise
            raise ValueError("No test_command option present in .testr.conf")
        elements = [command] + list(testargs)
        cmd = ' '.join(elements)
        idoption = ''
        if '$IDOPTION' in command:
            # IDOPTION is used, we must have it configured.
            try:
                idoption = parser.get('DEFAULT', 'test_id_option')
            except ConfigParser.NoOptionError as e:
                if e.message != "No option 'test_id_option' in section: 'DEFAULT'":
                    raise
                raise ValueError("No test_id_option option present in .testr.conf")
        listopt = ''
        if '$LISTOPT' in command:
            # LISTOPT is used, test_list_option must be configured.
            try:
                listopt = parser.get('DEFAULT', 'test_list_option')
            except ConfigParser.NoOptionError as e:
                if e.message != "No option 'test_list_option' in section: 'DEFAULT'":
                    raise
                raise ValueError("No test_list_option option present in .testr.conf")
        try:
            group_regex = parser.get('DEFAULT', 'group_regex')
        except ConfigParser.NoOptionError:
            group_regex = None
        if group_regex:
            def group_callback(test_id, regex=re.compile(group_regex)):
                match = regex.match(test_id)
                if match:
                    return match.group(0)
        else:
            group_callback = None
        if self.oldschool:
            listpath = os.path.join(self.ui.here, 'failing.list')
            result = self.run_factory(test_ids, cmd, listopt, idoption,
                self.ui, self.repository, listpath=listpath, parser=parser,
                test_filters=test_filters, instance_source=self,
                group_callback=group_callback)
        else:
            result = self.run_factory(test_ids, cmd, listopt, idoption,
                self.ui, self.repository, parser=parser,
                test_filters=test_filters, instance_source=self,
                group_callback=group_callback)
        return result

    def get_filter_tags(self):
        parser = self.get_parser()
        try:
            tags = parser.get('DEFAULT', 'filter_tags')
        except ConfigParser.NoOptionError as e:
            if e.message != "No option 'filter_tags' in section: 'DEFAULT'":
                raise
            return set()
        return set([tag.strip() for tag in tags.split()])

    def obtain_instance(self, concurrency):
        """If possible, get one or more test run environment instance ids.
        
        Note this is not threadsafe: calling it from multiple threads would
        likely result in shared results.
        """
        while len(self._instances) < concurrency:
            try:
                cmd = self.get_parser().get('DEFAULT', 'instance_provision')
            except ConfigParser.NoOptionError:
                # Instance allocation not configured
                return None
            variable_regex = '\$INSTANCE_COUNT'
            cmd = re.sub(variable_regex,
                str(concurrency - len(self._instances)), cmd)
            self.ui.output_values([('running', cmd)])
            proc = self.ui.subprocess_Popen(
                cmd, shell=True, stdout=subprocess.PIPE)
            out, _ = proc.communicate()
            if proc.returncode:
                raise ValueError('Provisioning instances failed, return %d' %
                    proc.returncode)
            new_instances = set([item.strip() for item in out.split()])
            self._instances.update(new_instances)
        # Cached first.
        available_instances = self._instances - self._allocated_instances
        # We only ask for instances when one should be available.
        result = available_instances.pop()
        self._allocated_instances.add(result)
        return result

    def release_instance(self, instance_id):
        """Return instance_ids to the pool for reuse."""
        self._allocated_instances.remove(instance_id)
