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
import itertools
import operator
import os.path
import re
import subprocess
import sys
import tempfile
from textwrap import dedent

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

    def __init__(self, test_ids, cmd_template, listopt, idoption, ui,
        repository, parallel=True, listpath=None):
        """Create a TestListingFixture.

        :param test_ids: The test_ids to use. May be None indicating that
            no ids filtering is requested: run whatever the test program
            chooses to.
        :param cmd_template: string to be filled out with
            IDFILE.
        :param listopt: Option to substitute into LISTOPT to cause test listing
            to take place.
        :param idoption: Option to substitutde into cmd when supplying any test
            ids.
        :param ui: The UI in use.
        :param repository: The repository to query for test times, if needed.
        :param parallel: If not True, prohibit parallel use : used to implement
            --parallel run recursively.
        :param listpath: The file listing path to use. If None, a unique path
            is created.
        """
        self.test_ids = test_ids
        self.template = cmd_template
        self.listopt = listopt
        self.idoption = idoption
        self.ui = ui
        self.repository = repository
        self.parallel = parallel
        self._listpath = listpath

    def setUp(self):
        super(TestListingFixture, self).setUp()
        variable_regex = '\$(IDOPTION|IDFILE|IDLIST|LISTOPT)'
        variables = {}
        cmd = self.template
        if self.test_ids is None:
            self.list_file_name = None
            name = ''
            self.test_ids = []
        else:
            name = self.make_listfile()
            variables['IDFILE'] = name
        idlist = ' '.join(self.test_ids)
        variables['IDLIST'] = idlist
        def subst(match):
            return variables.get(match.groups(1)[0], '')
        if not self.test_ids:
            # No test ids, no id option.
            idoption = ''
        else:
            idoption = re.sub(variable_regex, subst, self.idoption)
            variables['IDOPTION'] = idoption
        self.cmd = re.sub(variable_regex, subst, cmd)
        # and once more with list option support.
        variables['LISTOPT'] = self.listopt
        self.list_cmd = re.sub(variable_regex, subst, cmd)

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

    def list_tests(self):
        """List the tests returned by list_cmd.

        :return: A list of test ids.
        """
        if '$LISTOPT' not in self.template:
            raise ValueError("LISTOPT not configured in .testr.conf.")
        self.ui.output_values([('running', self.list_cmd)])
        run_proc = self.ui.subprocess_Popen(self.list_cmd, shell=True,
            stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        out, err = run_proc.communicate()
        # Should we raise on non-zero exit?
        ids = [id for id in out.split('\n') if id]
        return ids

    def run_tests(self):
        """Run the tests defined by the command and ui.

        :return: A list of spawned processes.
        """
        if not self.ui.options.parallel or not self.parallel:
            concurrency = 1
        else:
            concurrency = self.local_concurrency()
            if not concurrency:
                concurrency = 1
        if concurrency == 1:
            self.ui.output_values([('running', self.cmd)])
            run_proc = self.ui.subprocess_Popen(self.cmd, shell=True,
                stdout=subprocess.PIPE, stdin=subprocess.PIPE)
            # Prevent processes stalling if they read from stdin; we could
            # pass this through in future, but there is no point doing that
            # until we have a working can-run-debugger-inline story.
            run_proc.stdin.close()
            return [run_proc]
        result = []
        if not self.test_ids:
            # Discover the tests to run
            test_ids = self.list_tests()
        else:
            # Use the already requested tests.
            test_ids = self.test_ids
        test_id_groups = self.partition_tests(test_ids, concurrency)
        for test_ids in test_id_groups:
            if not test_ids:
                # No tests in this partition
                continue
            fixture = self.useFixture(TestListingFixture(test_ids,
                self.template, self.listopt, self.idoption, self.ui,
                self.repository, parallel=False))
            result.extend(fixture.run_tests())
        return result

    def partition_tests(self, test_ids, concurrency):
        """Parition test_ids by concurrency.

        Test durations from the repository are used to get partitions which
        have roughly the same expected runtime. New tests - those with no
        recorded duration - are allocated in round-robin fashion to the 
        partitions created using test durations.

        :return: A list where each element is a distinct subset of test_ids,
            and the union of all the elements is equal to set(test_ids).
        """
        partitions = [list() for i in range(concurrency)]
        timed_partitions = [[0.0, partition] for partition in partitions]
        time_data = self.repository.get_test_times(test_ids)
        timed = time_data['known']
        unknown = time_data['unknown']
        # Scheduling is NP complete in general, so we avoid aiming for
        # perfection. A quick approximation that is sufficient for our general
        # needs:
        # sort the tests by time
        # allocate to partitions by putting each test in to the partition with
        # the current lowest time.
        queue = sorted(timed.items(), key=operator.itemgetter(1), reverse=True)
        for test_id, duration in queue:
            timed_partitions[0][0] = timed_partitions[0][0] + duration
            timed_partitions[0][1].append(test_id)
            timed_partitions.sort(key=operator.itemgetter(0))
        # Assign tests with unknown times in round robin fashion to the partitions.
        for partition, test_id in itertools.izip(itertools.cycle(partitions), unknown):
            partition.append(test_id)
        return partitions

    def local_concurrency(self):
        if sys.platform == 'linux2':
            concurrency = None
            for line in file('/proc/cpuinfo', 'rb'):
                if line.startswith('processor'):
                    concurrency = int(line[line.find(':')+1:]) + 1
            return concurrency
        # No concurrency logic known.
        return None


class TestCommand(object):
    """Represents the test command defined in .testr.conf.
    
    :ivar run_factory: The fixture to use to execute a command.
    :ivar oldschool: Use failing.list rather than a unique file path.
    """
    
    run_factory = TestListingFixture
    oldschool = False

    def __init__(self, ui, repository):
        """Create a TestCommand.

        :param ui: A testrepository.ui.UI object which is used to obtain the
            location of the .testr.conf.
        :param repository: A testrepository.repository.Repository used for
            determining test times when partitioning tests.
        """
        self.ui = ui
        self.repository = repository

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
        idoption = ''
        if '$IDOPTION' in command:
            # IDOPTION is used, we must have it configured.
            try:
                idoption = parser.get('DEFAULT', 'test_id_option')
            except ConfigParser.NoOptionError, e:
                if e.message != "No option 'test_id_option' in section: 'DEFAULT'":
                    raise
                raise ValueError("No test_id_option option present in .testr.conf")
        listopt = ''
        if '$LISTOPT' in command:
            # LISTOPT is used, test_list_option must be configured.
            try:
                listopt = parser.get('DEFAULT', 'test_list_option')
            except ConfigParser.NoOptionError, e:
                if e.message != "No option 'test_list_option' in section: 'DEFAULT'":
                    raise
                raise ValueError("No test_list_option option present in .testr.conf")
        if self.oldschool:
            listpath = os.path.join(self.ui.here, 'failing.list')
            result = self.run_factory(test_ids, cmd, listopt, idoption,
                self.ui, self.repository, listpath=listpath)
        else:
            result = self.run_factory(test_ids, cmd, listopt, idoption,
                self.ui, self.repository)
        return result
