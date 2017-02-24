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

"""Run a projects tests and load them into stestr."""

from math import ceil
import os
import subprocess

import testtools

from stestr.commands import load
from stestr import config_file
from stestr import output
from stestr.repository import abstract as repository
from stestr.repository import util
from stestr.testlist import parse_list


def set_cli_opts(parser):
    parser.add_argument("--failing", action="store_true",
                        default=False,
                        help="Run only tests known to be failing.")
    parser.add_argument("--serial", action="store_true",
                        default=False,
                        help="Run tests in a serial processe.")
    parser.add_argument("--concurrency", action="store", default=0,
                        help="How many processes to use. The default (0) "
                             "autodetects your CPU count.")
    parser.add_argument("--load-list", default=None,
                        help="Only run tests listed in the named file."),
    parser.add_argument("--partial", action="store_true", default=False,
                        help="Only some tests will be run. Implied by "
                             "--failing.")
    parser.add_argument("--subunit", action="store_true", default=False,
                        help="Display results in subunit format.")
    parser.add_argument("--until-failure", action="store_true", default=False,
                        help="Repeat the run again and again until failure "
                             "occurs.")
    parser.add_argument("--analyze-isolation", action="store_true",
                        default=False,
                        help="Search the last test run for 2-test test "
                             "isolation interactions.")
    parser.add_argument("--isolated", action="store_true",
                        default=False,
                        help="Run each test id in a separate test runner.")
    parser.add_argument("--worker-file", action="store", default=None,
                        dest='worker_path',
                        help="Optional path of a manual worker grouping file "
                             "to use for the run")
    parser.add_argument('--blacklist-file', '-b',
                        default=None, dest='blacklist_file',
                        help='Path to a blacklist file, this file '
                             'contains a separate regex exclude on each '
                             'newline')
    parser.add_argument('--whitelist-file', '-w',
                        default=None, dest='whitelist_file',
                        help='Path to a whitelist file, this file '
                             'contains a separate regex on each newline.')
    parser.add_argument('--black-regex', '-B', default=None,
                        dest='black_regex',
                        help='Test rejection regex. If a test cases name '
                        'matches on re.search() operation , '
                        'it will be removed from the final test list. '
                        'Effectively the black-regexp is added to '
                        ' black regexp list, but you do need to edit a file. '
                        'The black filtering happens after the initial '
                        ' white selection, which by default is everything.')
    parser.add_argument('--no-discover', '-n', default=None, metavar='TEST_ID',
                        help="Takes in a single test to bypasses test discover"
                             " and just execute the test specified. A file "
                             "name may be used in place of a test name.")
    parser.add_argument('--random', '-r', action="store_true", default=False,
                        help="Randomize the test order after they are "
                             "partioned into separate workers")


def get_cli_help():
    help_str = "Run the tests for a project and load them into a repository."
    return help_str


def _find_failing(repo):
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


def run(arguments):
    args = arguments[0]
    filters = arguments[1] or None
    try:
        repo = util.get_repo_open(args.repo_type, args.repo_url)
    # If a repo is not found, and there a testr config exists just create it
    except repository.RepositoryNotFound:
        if not os.path.isfile(args.config):
            raise
        repo = util.get_repo_initialise(args.repo_type, args.repo_url)
    if args.no_discover:
        ids = args.no_discover
        if ids.find('/') != -1:
            root, _ = os.path.splitext(ids)
            ids = root.replace('/', '.')
        run_cmd = 'python -m subunit.run ' + ids

        def run_tests():
            run_proc = [('subunit', output.ReturnCodeToSubunit(
                subprocess.Popen(run_cmd, shell=True,
                                 stdout=subprocess.PIPE)))]
            return load.load((None, None), in_streams=run_proc,
                             partial=args.partial, subunit_out=args.subunit,
                             repo_type=args.repo_type,
                             repo_url=args.repo_url)

        if not args.until_failure:
            return run_tests()
        else:
            result = run_tests()
            while not result:
                result = run_tests()
            return result

    if args.failing or args.analyze_isolation:
        ids = _find_failing(repo)
    else:
        ids = None
    if args.load_list:
        list_ids = set()
        # Should perhaps be text.. currently does its own decode.
        with open(args.load_list, 'rb') as list_file:
            list_ids = set(parse_list(list_file.read()))
        if ids is None:
            # Use the supplied list verbatim
            ids = list_ids
        else:
            # We have some already limited set of ids, just reduce to ids
            # that are both failing and listed.
            ids = list_ids.intersection(ids)

    conf = config_file.TestrConf(args.config)
    if not args.analyze_isolation:
        cmd = conf.get_run_command(args, ids, filters)
        if args.isolated:
            result = 0
            cmd.setUp()
            try:
                ids = cmd.list_tests()
            finally:
                cmd.cleanUp()
            for test_id in ids:
                # TODO(mtreinish): add regex
                cmd = conf.get_run_command(args, [test_id], filters)
                run_result = _run_tests(cmd, args.failing,
                                        args.analyze_isolation,
                                        args.isolated,
                                        args.until_failure,
                                        subunit_out=args.subunit)
                if run_result > result:
                    result = run_result
            return result
        else:
            return _run_tests(cmd, args.failing, args.analyze_isolation,
                              args.isolated, args.until_failure,
                              subunit_out=args.subunit)
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
            # TODO(mtrienish): Add regex
            cmd = conf.get_run_command(args, [test_id])
            if not _run_tests(cmd):
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
            candidate_causes = _prior_tests(
                latest_run, spurious_failure)
            bottom = 0
            top = len(candidate_causes)
            width = top - bottom
            while width:
                check_width = int(ceil(width / 2.0))
                # TODO(mtreinish): Add regex
                cmd = conf.get_run_command(
                    args,
                    candidate_causes[bottom:bottom + check_width]
                    + [spurious_failure])
                _run_tests(cmd)
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
            output.output_table(table)
            return 3
        return 0


def _prior_tests(self, run, failing_id):
    """Calculate what tests from the test run run ran before test_id.

    Tests that ran in a different worker are not included in the result.
    """
    if not getattr(self, '_worker_to_test', False):
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


def _run_tests(cmd, failing, analyze_isolation, isolated, until_failure,
               subunit_out=False):
    """Run the tests cmd was parameterised with."""
    cmd.setUp()
    try:
        def run_tests():
            run_procs = [('subunit',
                          output.ReturnCodeToSubunit(
                              proc)) for proc in cmd.run_tests()]
            partial = False
            if (failing or analyze_isolation or isolated):
                partial = True
            if not run_procs:
                print("The specified regex doesn't match with anything.")
                return 0
            return load.load((None, None), in_streams=run_procs,
                             partial=partial, subunit_out=subunit_out,
                             repo_type=cmd.options.repo_type,
                             repo_url=cmd.options.repo_url)

        if not until_failure:
            return run_tests()
        else:
            result = run_tests()
            while not result:
                result = run_tests()
            return result
    finally:
        cmd.cleanUp()
