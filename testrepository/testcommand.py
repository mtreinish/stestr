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

from testrepository.results import TestResultFilter
from testrepository.testlist import (
    parse_list,
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
        repository, parallel=True, listpath=None, parser=None):
        """Create a TestListingFixture.

        :param test_ids: The test_ids to use. May be None indicating that
            no ids filtering is requested: run whatever the test program
            chooses to. For parallel runs None has to be expandable via
            either a default value or a LISTOPT.
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
        :param parser: An options parser for reading options from.
        """
        self.test_ids = test_ids
        self.template = cmd_template
        self.listopt = listopt
        self.idoption = idoption
        self.ui = ui
        self.repository = repository
        self.parallel = parallel
        self._listpath = listpath
        self._parser = parser

    def setUp(self):
        super(TestListingFixture, self).setUp()
        variable_regex = '\$(IDOPTION|IDFILE|IDLIST|LISTOPT)'
        variables = {}
        list_variables = {'LISTOPT': self.listopt}
        cmd = self.template
        try:
            default_idstr = self._parser.get('DEFAULT', 'test_id_list_default')
            list_variables['IDLIST'] = default_idstr
            # In theory we should also support casting this into IDFILE etc -
            # needs this horrible class refactored.
        except ConfigParser.NoOptionError, e:
            if e.message != "No option 'test_id_list_default' in section: 'DEFAULT'":
                raise
            default_idstr = None
        def list_subst(match):
            return list_variables.get(match.groups(1)[0], '')
        self.list_cmd = re.sub(variable_regex, list_subst, cmd)
        nonparallel = (not self.parallel or not
            getattr(self.ui, 'options', None) or not
            getattr(self.ui.options, 'parallel', None))
        if nonparallel:
            self.concurrency = 1
        else:
            self.concurrency = self.ui.options.concurrency
            if not self.concurrency:
                self.concurrency = self.local_concurrency()
            if not self.concurrency:
                self.concurrency = 1
        if self.test_ids is None:
            if self.concurrency == 1:
                if default_idstr:
                    self.test_ids = default_idstr.split()
            if self.concurrency != 1:
                # Have to be able to tell each worker what to run.
                self.test_ids = self.list_tests()
        if self.test_ids is None:
            # No test ids to supply to the program.
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
            write_list(stream, self.test_ids)
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
            raise ValueError("LISTOPT not configured in .testr.conf")
        self.ui.output_values([('running', self.list_cmd)])
        run_proc = self.ui.subprocess_Popen(self.list_cmd, shell=True,
            stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        out, err = run_proc.communicate()
        # Should we raise on non-zero exit?
        ids = parse_list(out)
        return ids

    def run_tests(self):
        """Run the tests defined by the command and ui.

        :return: A list of spawned processes.
        """
        result = []
        test_ids = self.test_ids
        if self.concurrency == 1:
            self.ui.output_values([('running', self.cmd)])
            run_proc = self.ui.subprocess_Popen(self.cmd, shell=True,
                stdout=subprocess.PIPE, stdin=subprocess.PIPE)
            # Prevent processes stalling if they read from stdin; we could
            # pass this through in future, but there is no point doing that
            # until we have a working can-run-debugger-inline story.
            run_proc.stdin.close()
            return [run_proc]
        test_id_groups = self.partition_tests(test_ids, self.concurrency)
        for test_ids in test_id_groups:
            if not test_ids:
                # No tests in this partition
                continue
            fixture = self.useFixture(TestListingFixture(test_ids,
                self.template, self.listopt, self.idoption, self.ui,
                self.repository, parallel=False, parser=self._parser))
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
        # the current (lowest time, shortest length)
        queue = sorted(timed.items(), key=operator.itemgetter(1), reverse=True)
        for test_id, duration in queue:
            timed_partitions[0][0] = timed_partitions[0][0] + duration
            timed_partitions[0][1].append(test_id)
            timed_partitions.sort(key=lambda item:(item[0], len(item[1])))
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

    def get_parser(self):
        """Get a parser with the .testr.conf in it."""
        parser = ConfigParser.ConfigParser()
        # This possibly should push down into UI.
        if self.ui.here == 'memory:':
            return parser
        if not parser.read(os.path.join(self.ui.here, '.testr.conf')):
            raise ValueError("No .testr.conf config file")
        return parser

    def get_run_command(self, test_ids=None, testargs=()):
        """Get the command that would be run to run tests."""
        parser = self.get_parser()
        try:
            command = parser.get('DEFAULT', 'test_command')
        except ConfigParser.NoOptionError, e:
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
                self.ui, self.repository, listpath=listpath, parser=parser)
        else:
            result = self.run_factory(test_ids, cmd, listopt, idoption,
                self.ui, self.repository, parser=parser)
        return result

    def get_filter_tags(self):
        parser = self.get_parser()
        try:
            tags = parser.get('DEFAULT', 'filter_tags')
        except ConfigParser.NoOptionError, e:
            if e.message != "No option 'filter_tags' in section: 'DEFAULT'":
                raise
            return set()
        return set([tag.strip() for tag in tags.split()])

    def make_result(self, receiver):
        """Create a TestResult that will perform any global filtering etc.

        :param receiver: The result to forward the result of global filtering.
        :return: A TestResult.
        """
        filter_tags = self.get_filter_tags()
        if filter_tags:
            try:
                from subunit.test_results import make_tag_filter
            except ImportError:
                raise ValueError(
                    "Subunit not installed or does not have tag filtering support")
            # predicates return False to filter something out. We want to
            # filter out tagged tests *unless* they fail/error. So we want
            # tag_p:False + outcome_p:False -> False
            # tag_p:False + outcome_p:True -> True
            # tag_p:True + * -> True
            def error_or_fail(t, outcome, e, d, tags):
                return outcome in ('error', 'failure')
            def or_predicates(predicates):
                def fn(*args, **kwargs):
                    for predicate in predicates:
                        if predicate(*args, **kwargs):
                            return True
                    return False
                return fn
            predicates = [make_tag_filter(None, filter_tags), error_or_fail]
            predicate = or_predicates(predicates)
            return TestResultFilter(
                receiver, filter_success=False, filter_predicate=predicate)
        return receiver
