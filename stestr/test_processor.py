# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import re
import signal
import subprocess
import sys
import tempfile

import fixtures
import six
from subunit import v2

from stestr import results
from stestr import scheduler
from stestr import selection
from stestr import testlist


class TestProcessorFixture(fixtures.Fixture):
    """Write a temporary file to disk with test ids in it.

    The TestProcessorFixture is used to handle the lifecycle of running
    the subunit.run commands. A fixture is used for this class to handle
    the temporary list files creation.

    :param test_ids: The test_ids to use. May be None indicating that
        no ids are known and they should be discovered by listing or
        configuration if they must be known to run tests. Test ids are
        needed to run tests when filtering or partitioning is needed: if
        the run concurrency is > 1 partitioning is needed, and filtering is
        needed if the user has passed in filters.
    :param cmd_template: string to be used for the command that will be
        filled out with the IDFILE when it is created.
    :param listopt: Option to substitute into LISTOPT to cause test listing
                    to take place.
    :param idoption: Option to substitute into cmd when supplying any test ids.
    :param repository: The repository to query for test times, if needed.
    :param parallel: If not True, prohibit parallel use : used to implement
                     --parallel run recursively.
    :param listpath: The file listing path to use. If None, a unique path
                     is created.
    :param test_filters: An optional list of test filters to apply. Each
        filter should be a string suitable for passing to re.compile.
        Filters are applied using search() rather than match(), so if
        anchoring is needed it should be included in the regex.
        The test ids used for executing are the union of all the
        individual filters: to take the intersection instead, craft a
        single regex that matches all your criteria. Filters are
        automatically applied by run_tests(), or can be applied by calling
        filter_tests(test_ids).
    :param group_callback: If supplied, should be a function that accepts a
        test id and returns a group id. A group id is an arbitrary value
        used as a dictionary key in the scheduler. All test ids with the
        same group id are scheduled onto the same backend test process.
    :param bool serial: Run tests serially
    :param path worker_path: Optional path of a manual worker grouping file
        to use for the run
    :param int concurrency: How many processes to use. The default (0)
        autodetects your CPU count and uses that.
    :param path blacklist_file: Path to a blacklist file, this file contains a
        separate regex exclude on each newline.
    :param path whitelist_file: Path to a whitelist file, this file contains a
         separate regex on each newline.
    :param boolean randomize: Randomize the test order after they are
        partitioned into separate workers
    """

    def __init__(self, test_ids, cmd_template, listopt, idoption,
                 repository, parallel=True, listpath=None,
                 test_filters=None, group_callback=None, serial=False,
                 worker_path=None, concurrency=0, blacklist_file=None,
                 black_regex=None, whitelist_file=None, randomize=False):
        """Create a TestProcessorFixture."""

        self.test_ids = test_ids
        self.template = cmd_template
        self.listopt = listopt
        self.idoption = idoption
        self.repository = repository
        self.parallel = parallel
        if serial:
            self.parallel = False
        self._listpath = listpath
        self.test_filters = test_filters
        self._group_callback = group_callback
        self.worker_path = None
        self.worker_path = worker_path
        self.concurrency_value = concurrency
        self.blacklist_file = blacklist_file
        self.whitelist_file = whitelist_file
        self.black_regex = black_regex
        self.randomize = randomize

    def setUp(self):
        super(TestProcessorFixture, self).setUp()
        variable_regex = '\$(IDOPTION|IDFILE|IDLIST|LISTOPT)'
        variables = {}
        list_variables = {'LISTOPT': self.listopt}
        cmd = self.template
        default_idstr = None

        def list_subst(match):
            return list_variables.get(match.groups(1)[0], '')

        self.list_cmd = re.sub(variable_regex, list_subst, cmd)
        nonparallel = not self.parallel
        selection_logic = (self.test_filters or self.blacklist_file or
                           self.whitelist_file or self.black_regex)
        if nonparallel:
            self.concurrency = 1
        else:
            self.concurrency = None
            if self.concurrency_value:
                self.concurrency = int(self.concurrency_value)
            if not self.concurrency:
                self.concurrency = scheduler.local_concurrency()
            if not self.concurrency:
                self.concurrency = 1
        if self.test_ids is None:
            if self.concurrency == 1:
                if default_idstr:
                    self.test_ids = default_idstr.split()
            if self.concurrency != 1 or selection_logic or self.worker_path:
                # Have to be able to tell each worker what to run / filter
                # tests.
                self.test_ids = self.list_tests()
        if self.test_ids is None:
            # No test ids to supply to the program.
            self.list_file_name = None
            name = ''
            idlist = ''
        else:
            self.test_ids = selection.construct_list(
                self.test_ids, blacklist_file=self.blacklist_file,
                whitelist_file=self.whitelist_file,
                regexes=self.test_filters,
                black_regex=self.black_regex)
            name = self.make_listfile()
            variables['IDFILE'] = name
            idlist = ' '.join(self.test_ids)
        variables['IDLIST'] = idlist

        def subst(match):
            return variables.get(match.groups(1)[0], '')

        if self.test_ids is None:
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
            with stream:
                self.list_file_name = name
                testlist.write_list(stream, self.test_ids)
        except Exception:
            if name:
                os.unlink(name)
            raise
        self.addCleanup(os.unlink, name)
        return name

    def _clear_SIGPIPE(self):
        """Clear SIGPIPE : child processes expect the default handler."""
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    def _start_process(self, cmd):
        # NOTE(claudiub): Windows does not support passing in a preexec_fn
        # argument.
        preexec_fn = None if sys.platform == 'win32' else self._clear_SIGPIPE
        return subprocess.Popen(cmd, shell=True,
                                stdout=subprocess.PIPE,
                                stdin=subprocess.PIPE,
                                preexec_fn=preexec_fn)

    def list_tests(self):
        """List the tests returned by list_cmd.

        :return: A list of test ids.
        """
        run_proc = self._start_process(self.list_cmd)
        out, err = run_proc.communicate()
        if run_proc.returncode != 0:
            sys.stdout.write("\n=========================\n"
                             "Failures during discovery"
                             "\n=========================\n")
            new_out = six.BytesIO()
            v2.ByteStreamToStreamResult(
                six.BytesIO(out), 'stdout').run(
                    results.CatFiles(new_out))
            out = new_out.getvalue()
            if out:
                sys.stdout.write(six.text_type(out))
            if err:
                sys.stderr.write(six.text_type(err))
            sys.stdout.write("\n" + "=" * 80 + "\n"
                             "The above traceback was encountered during "
                             "test discovery which imports all the found test"
                             " modules in the specified test_path.\n")
            exit(100)
        ids = testlist.parse_enumeration(out)
        return ids

    def run_tests(self):
        """Run the tests defined by the command

        :return: A list of spawned processes.
        """
        result = []
        test_ids = self.test_ids
        # Handle the single worker case (this is also run recursively per
        # worker in the parallel case)
        if self.concurrency == 1 and (test_ids is None or test_ids):
            run_proc = self._start_process(self.cmd)
            # Prevent processes stalling if they read from stdin; we could
            # pass this through in future, but there is no point doing that
            # until we have a working can-run-debugger-inline story.
            run_proc.stdin.close()
            return [run_proc]
        # If there is a worker path, use that to get worker groups
        elif self.worker_path:
            test_id_groups = scheduler.generate_worker_partitions(
                test_ids, self.worker_path, self.repository,
                self._group_callback, self.randomize)
        # If we have multiple workers partition the tests and recursively
        # create single worker TestProcessorFixtures for each worker
        else:
            test_id_groups = scheduler.partition_tests(test_ids,
                                                       self.concurrency,
                                                       self.repository,
                                                       self._group_callback)
        for test_ids in test_id_groups:
            if not test_ids:
                # No tests in this partition
                continue
            fixture = self.useFixture(
                TestProcessorFixture(test_ids,
                                     self.template, self.listopt,
                                     self.idoption, self.repository,
                                     parallel=False))
            result.extend(fixture.run_tests())
        return result
