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


from stestr import output
from stestr import results
from stestr import scheduler
from stestr import selection
from stestr import testlist
from stestr import utils


class TestListingFixture(fixtures.Fixture):
    """Write a temporary file to disk with test ids in it."""

    def __init__(self, test_ids, options, cmd_template, listopt, idoption,
                 repository, parallel=True, listpath=None,
                 parser=None, test_filters=None, instance_source=None,
                 group_callback=None):
        """Create a TestListingFixture.

        :param test_ids: The test_ids to use. May be None indicating that
            no ids are known and they should be discovered by listing or
            configuration if they must be known to run tests. Test ids are
            needed to run tests when filtering or partitioning is needed: if
            the run concurrency is > 1 partitioning is needed, and filtering is
            needed if the user has passed in filters.
        :param cmd_template: string to be filled out with IDFILE
        :param listopt: Option to substitute into LISTOPT to cause test listing
                        to take place.
        :param idoption: Option to substitutde into cmd when supplying any test
                         ids.
        :param repository: The repository to query for test times, if needed.
        :param parallel: If not True, prohibit parallel use : used to implement
                         --parallel run recursively.
        :param listpath: The file listing path to use. If None, a unique path
                         is created.
        :param parser: An options parser for reading options from.
        :param test_filters: An optional list of test filters to apply. Each
            filter should be a string suitable for passing to re.compile.
            filters are applied using search() rather than match(), so if
            anchoring is needed it should be included in the regex.
            The test ids used for executing are the union of all the
            individual filters: to take the intersection instead, craft a
            single regex that matches all your criteria. Filters are
            automatically applied by run_tests(), or can be applied by calling
            filter_tests(test_ids).
        :param instance_source: A source of test run instances. Must support
            obtain_instance(max_concurrency) -> id and release_instance(id)
            calls.
        :param group_callback: If supplied, should be a function that accepts a
            test id and returns a group id. A group id is an arbitrary value
            used as a dictionary key in the scheduler. All test ids with the
            same group id are scheduled onto the same backend test process.
        """
        self.test_ids = test_ids
        self.template = cmd_template
        self.listopt = listopt
        self.idoption = idoption
        self.repository = repository
        self.parallel = parallel
        self._listpath = listpath
        self._parser = parser
        self.test_filters = test_filters
        self._group_callback = group_callback
        self._instance_source = instance_source
        self.options = options

    def setUp(self):
        super(TestListingFixture, self).setUp()
        variable_regex = '\$(IDOPTION|IDFILE|IDLIST|LISTOPT)'
        variables = {}
        list_variables = {'LISTOPT': self.listopt}
        cmd = self.template
        default_idstr = None

        def list_subst(match):
            return list_variables.get(match.groups(1)[0], '')

        self.list_cmd = re.sub(variable_regex, list_subst, cmd)
        nonparallel = not self.parallel
        if nonparallel:
            self.concurrency = 1
        else:
            self.concurrency = None
            if hasattr(self.options, 'concurrency'):
                self.concurrency = int(self.options.concurrency)
            if not self.concurrency:
                self.concurrency = scheduler.local_concurrency()
            if not self.concurrency:
                self.concurrency = 1
        if self.test_ids is None:
            if self.concurrency == 1:
                if default_idstr:
                    self.test_ids = default_idstr.split()
            if self.concurrency != 1 or self.test_filters is not None:
                # Have to be able to tell each worker what to run / filter
                # tests.
                self.test_ids = self.list_tests()
        if self.test_ids is None:
            # No test ids to supply to the program.
            self.list_file_name = None
            name = ''
            idlist = ''
        else:
            self.test_ids = selection.filter_tests(self.test_filters,
                                                   self.test_ids)
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
            self.list_file_name = name
            testlist.write_list(stream, self.test_ids)
            stream.close()
        except Exception:
            if name:
                os.unlink(name)
            raise
        self.addCleanup(os.unlink, name)
        return name

    def _clear_SIGPIPE(self):
        """Clear SIGPIPE : child processes expect the default handler."""
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    def list_tests(self):
        """List the tests returned by list_cmd.

        :return: A list of test ids.
        """
        if '$LISTOPT' not in self.template:
            raise ValueError("LISTOPT not configured in .testr.conf")
        instance, list_cmd = self._per_instance_command(self.list_cmd)
        try:
            output.output_values([('running', list_cmd)])
            run_proc = subprocess.Popen(list_cmd, shell=True,
                                        stdout=subprocess.PIPE,
                                        stdin=subprocess.PIPE,
                                        preexec_fn=self._clear_SIGPIPE)
            out, err = run_proc.communicate()
            if run_proc.returncode != 0:
                new_out = six.BytesIO()
                v2.ByteStreamToStreamResult(
                    six.BytesIO(out), 'stdout').run(
                        results.CatFiles(new_out))
                out = new_out.getvalue()
                sys.stdout.write(six.text_type(out))
                sys.stderr.write(six.text_type(err))
                raise ValueError(
                    "Non-zero exit code (%d) from test listing."
                    % (run_proc.returncode))
            ids = testlist.parse_enumeration(out)
            return ids
        finally:
            if instance:
                self._instance_source.release_instance(instance)

    def _per_instance_command(self, cmd):
        """Customise cmd to with an instance-id.

        :param concurrency: The number of instances to ask for (used to avoid
            death-by-1000 cuts of latency.
        """
        if self._instance_source is None:
            return None, cmd
        instance = self._instance_source.obtain_instance(self.concurrency)
        return instance, cmd

    def run_tests(self):
        """Run the tests defined by the command and ui.

        :return: A list of spawned processes.
        """
        result = []
        test_ids = self.test_ids
        # Handle the single worker case (this is also run recursivly per worker
        # Un the parallel case
        if self.concurrency == 1 and (test_ids is None or test_ids):
            # Have to customise cmd here, as instances are allocated
            # just-in-time. XXX: Indicates this whole region needs refactoring.
            instance, cmd = self._per_instance_command(self.cmd)
            output.output_values([('running', cmd)])
            run_proc = subprocess.Popen(
                cmd, shell=True,
                stdout=subprocess.PIPE, stdin=subprocess.PIPE,
                preexec_fn=self._clear_SIGPIPE)
            # Prevent processes stalling if they read from stdin; we could
            # pass this through in future, but there is no point doing that
            # until we have a working can-run-debugger-inline story.
            run_proc.stdin.close()
            if instance:
                return [utils.CallWhenProcFinishes(run_proc,
                        lambda:self._instance_source.release_instance(
                            instance))]
            else:
                return [run_proc]
        test_id_groups = scheduler.partition_tests(test_ids, self.concurrency,
                                                   self.repository,
                                                   self._group_callback)
        for test_ids in test_id_groups:
            if not test_ids:
                # No tests in this partition
                continue
            fixture = self.useFixture(
                TestListingFixture(test_ids, self.options,
                                   self.template, self.listopt, self.idoption,
                                   self.repository, parallel=False,
                                   parser=self._parser,
                                   instance_source=self._instance_source))
            result.extend(fixture.run_tests())
        return result
