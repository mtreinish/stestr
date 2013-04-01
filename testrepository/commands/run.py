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

from io import BytesIO
from math import ceil
import optparse
import re

from extras import try_import
import subunit
v2_avail = try_import('subunit.ByteStreamToStreamResult')
import testtools
from testtools import (
    TestByTestResult,
    )
from testtools.compat import _b

from testrepository.arguments.doubledash import DoubledashArgument
from testrepository.arguments.string import StringArgument
from testrepository.commands import Command
from testrepository.commands.load import load
from testrepository.ui import decorator
from testrepository.testcommand import TestCommand, testrconf_help
from testrepository.testlist import parse_list


LINEFEED = _b('\n')[0]


class ReturnCodeToSubunit(object):
    """Converts a process return code to a subunit error on the process stdout.

    The ReturnCodeToSubunit object behaves as a readonly stream, supplying
    the read, readline and readlines methods. If the process exits non-zero a
    synthetic test is added to the output, making the error accessible to
    subunit stream consumers. If the process closes its stdout and then does
    not terminate, reading from the ReturnCodeToSubunit stream will hang.

    This class will be deleted at some point, allowing parsing to read from the
    actual fd and benefit from select for aggregating non-subunit output.
    """

    def __init__(self, process):
        """Adapt a process to a readable stream.

        :param process: A subprocess.Popen object that is
            generating subunit.
        """
        self.proc = process
        self.done = False
        self.source = self.proc.stdout
        self.lastoutput = LINEFEED

    def _append_return_code_as_test(self):
        if self.done is True:
            return
        self.source = BytesIO()
        returncode = self.proc.wait()
        if returncode != 0:
            if self.lastoutput != LINEFEED:
                # Subunit V1 is line orientated, it has to start on a fresh
                # line. V2 needs to start on any fresh utf8 character border
                # - which is not guaranteed in an arbitrary stream endpoint, so
                # injecting a \n gives us such a guarantee.
                self.source.write(_b('\n'))
            if v2_avail:
                stream = subunit.StreamResultToBytes(self.source)
                stream.status(test_id='process-returncode', test_status='fail',
                    file_name='traceback', mime_type='test/plain;charset=utf8',
                    file_bytes=('returncode %d' % returncode).encode('utf8'))
            else:
                self.source.write(_b('test: process-returncode\n'
                    'failure: process-returncode [\n'
                    ' returncode %d\n'
                    ']\n' % returncode))
        self.source.seek(0)
        self.done = True

    def read(self, count=-1):
        if count == 0:
            return _b('')
        result = self.source.read(count)
        if result:
            self.lastoutput = result[-1]
            return result
        self._append_return_code_as_test()
        return self.source.read(count)

    def readline(self):
        result = self.source.readline()
        if result:
            self.lastoutput = result[-1]
            return result
        self._append_return_code_as_test()
        return self.source.readline()

    def readlines(self):
        result = self.source.readlines()
        if result:
            self.lastoutput = result[-1][-1]
        self._append_return_code_as_test()
        result.extend(self.source.readlines())
        return result


class run(Command):
    __doc__ = """Run the tests for a project and load them into testrepository.
    """ + testrconf_help

    options = [
        optparse.Option("--failing", action="store_true",
            default=False, help="Run only tests known to be failing."),
        optparse.Option("--parallel", action="store_true",
            default=False, help="Run tests in parallel processes."),
        optparse.Option("--concurrency", action="store", type="int", default=0,
            help="How many processes to use. The default (0) autodetects your CPU count."),
        optparse.Option("--load-list", default=None,
            help="Only run tests listed in the named file."),
        optparse.Option("--partial", action="store_true",
            default=False,
            help="Only some tests will be run. Implied by --failing."),
        optparse.Option("--subunit", action="store_true",
            default=False, help="Display results in subunit format."),
        optparse.Option("--full-results", action="store_true",
            default=False,
            help="No-op - deprecated and kept only for backwards compat."),
        optparse.Option("--until-failure", action="store_true",
            default=False,
            help="Repeat the run again and again until failure occurs."),
        optparse.Option("--analyze-isolation", action="store_true",
            default=False,
            help="Search the last test run for 2-test test isolation interactions."),
        ]
    args = [StringArgument('testfilters', 0, None), DoubledashArgument(),
        StringArgument('testargs', 0, None)]
    # Can be assigned to to inject a custom command factory.
    command_factory = TestCommand

    def _find_failing(self, repo):
        run = repo.get_failing()
        case = run.get_test()
        ids = []
        def gather_errors(test_dict):
            if test_dict['status'] == 'fail':
                ids.append(test_dict['id'])
        result = testtools.StreamToDict(gather_errors)
        result.startTestRun()
        try:
            case.run(result)
        finally:
            result.stopTestRun()
        return ids

    def run(self):
        repo = self.repository_factory.open(self.ui.here)
        if self.ui.options.failing or self.ui.options.analyze_isolation:
            ids = self._find_failing(repo)
        else:
            ids = None
        if self.ui.options.load_list:
            list_ids = set()
            # Should perhaps be text.. currently does its own decode.
            with open(self.ui.options.load_list, 'rb') as list_file:
                list_ids = set(parse_list(list_file.read()))
            if ids is None:
                # Use the supplied list verbatim
                ids = list_ids
            else:
                # We have some already limited set of ids, just reduce to ids
                # that are both failing and listed.
                ids = list_ids.intersection(ids)
        if self.ui.arguments['testfilters']:
            filters = self.ui.arguments['testfilters']
        else:
            filters = None
        testcommand = self.command_factory(self.ui, repo)
        testcommand.setUp()
        try:
            if not self.ui.options.analyze_isolation:
                cmd = testcommand.get_run_command(ids, self.ui.arguments['testargs'],
                    test_filters = filters)
                return self._run_tests(cmd)
            else:
                # Where do we source data about the cause of conflicts.
                # XXX: Should instead capture the run id in with the failing test
                # data so that we can deal with failures split across many partial
                # runs.
                latest_run = repo.get_latest_run()
                # Stage one: reduce the list of failing tests (possibly further
                # reduced by testfilters) to eliminate fails-on-own tests.
                spurious_failures = set()
                for test_id in ids:
                    cmd = testcommand.get_run_command([test_id],
                        self.ui.arguments['testargs'], test_filters = filters)
                    if not self._run_tests(cmd):
                        # If the test was filtered, it won't have been run.
                        if test_id in repo.get_test_ids(repo.latest_id()):
                            spurious_failures.add(test_id)
                        # This is arguably ugly, why not just tell the system that
                        # a pass here isn't a real pass? [so that when we find a
                        # test that is spuriously failing, we don't forget
                        # that it is actually failng.
                        # Alternatively, perhaps this is a case for data mining:
                        # when a test starts passing, keep a journal, and allow
                        # digging back in time to see that it was a failure,
                        # what it failed with etc...
                        # The current solution is to just let it get marked as
                        # a pass temporarily.
                if not spurious_failures:
                    # All done.
                    return 0
                # spurious-failure -> cause.
                test_conflicts = {}
                for spurious_failure in spurious_failures:
                    candidate_causes = self._prior_tests(
                        latest_run, spurious_failure)
                    bottom = 0
                    top = len(candidate_causes)
                    width = top - bottom
                    while width:
                        check_width = int(ceil(width / 2.0))
                        cmd = testcommand.get_run_command(
                            candidate_causes[bottom:bottom + check_width]
                            + [spurious_failure],
                            self.ui.arguments['testargs'])
                        self._run_tests(cmd)
                        # check that the test we're probing still failed - still
                        # awkward.
                        found_fail = []
                        def find_fail(test_dict):
                            if test_dict['id'] == spurious_failure:
                                found_fail.append(True)
                        checker = testtools.StreamToDict(find_fail)
                        checker.startTestRun()
                        try:
                            repo.get_failing().get_test().run(checker)
                        finally:
                            checker.stopTestRun()
                        if found_fail:
                            # Our conflict is in bottom - clamp the range down.
                            top = bottom + check_width
                            if width == 1:
                                # found the cause
                                test_conflicts[
                                    spurious_failure] = candidate_causes[bottom]
                                width = 0
                            else:
                                width = top - bottom
                        else:
                            # Conflict in the range we did not run: discard bottom.
                            bottom = bottom + check_width
                            if width == 1:
                                # there will be no more to check, so we didn't
                                # reproduce the failure.
                                width = 0
                            else:
                                width = top - bottom
                    if spurious_failure not in test_conflicts:
                        # Could not determine cause
                        test_conflicts[spurious_failure] = 'unknown - no conflicts'
                if test_conflicts:
                    table = [('failing test', 'caused by test')]
                    for failure, causes in test_conflicts.items():
                        table.append((failure, causes))
                    self.ui.output_table(table)
                    return 3
                return 0
        finally:
            testcommand.cleanUp()

    def _prior_tests(self, run, failing_id):
        """Calculate what tests from the test run run ran before test_id.

        Tests that ran in a different worker are not included in the result.
        """
        if not getattr(self, '_worker_to_test', False):
            # TODO: switch to route codes?
            case = run.get_test()
            # Use None if there is no worker-N tag
            # If there are multiple, map them all.
            # (worker-N -> [testid, ...])
            worker_to_test = {}
            # (testid -> [workerN, ...])
            test_to_worker = {}
            def map_test(test_dict):
                tags = test_dict['tags']
                id = test_dict['id']
                workers = []
                for tag in tags:
                    if tag.startswith('worker-'):
                        workers.append(tag)
                if not workers:
                    workers = [None]
                for worker in workers:
                    worker_to_test.setdefault(worker, []).append(id)
                test_to_worker.setdefault(id, []).extend(workers)
            mapper = testtools.StreamToDict(map_test)
            mapper.startTestRun()
            try:
                case.run(mapper)
            finally:
                mapper.stopTestRun()
            self._worker_to_test = worker_to_test
            self._test_to_worker = test_to_worker
        failing_workers = self._test_to_worker[failing_id]
        prior_tests = []
        for worker in failing_workers:
            worker_tests = self._worker_to_test[worker]
            prior_tests.extend(worker_tests[:worker_tests.index(failing_id)])
        return prior_tests

    def _run_tests(self, cmd):
        """Run the tests cmd was parameterised with."""
        cmd.setUp()
        try:
            def run_tests():
                run_procs = [('subunit', ReturnCodeToSubunit(proc)) for proc in cmd.run_tests()]
                options = {}
                if self.ui.options.failing or self.ui.options.analyze_isolation:
                    options['partial'] = True
                load_ui = decorator.UI(input_streams=run_procs, options=options,
                    decorated=self.ui)
                load_cmd = load(load_ui)
                return load_cmd.execute()
            if not self.ui.options.until_failure:
                return run_tests()
            else:
                result = run_tests()
                while not result:
                    result = run_tests()
                return result
        finally:
            cmd.cleanUp()
