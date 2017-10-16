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

import math

import testtools

from stestr import output


class IsolationAnalyzer(object):

    def __init__(self, latest_run, conf, run_func, repo, test_path=None,
                 top_dir=None, group_regex=None, repo_type='file',
                 repo_url=None, serial=False, concurrency=0):
        super(IsolationAnalyzer, self).__init__()
        self._worker_to_test = None
        self._test_to_worker = None
        self.latest_run = latest_run
        self.conf = conf
        self.group_regex = group_regex
        self.repo_type = repo_type
        self.repo_url = repo_url
        self.serial = serial
        self.concurrency = concurrency
        self.test_path = test_path
        self.top_dir = top_dir
        self.run_func = run_func
        self.repo = repo

    def bisect_tests(self, spurious_failures):

        test_conflicts = {}
        if not spurious_failures:
            raise ValueError('No failures provided to bisect the cause of')
        for spurious_failure in spurious_failures:
            candidate_causes = self._prior_tests(self.latest_run,
                                                 spurious_failure)
            bottom = 0
            top = len(candidate_causes)
            width = top - bottom
            while width:
                check_width = int(math.ceil(width / 2.0))
                test_ids = candidate_causes[
                    bottom:bottom + check_width] + [spurious_failure]
                cmd = self.conf.get_run_command(
                    test_ids, group_regex=self.group_regex,
                    repo_type=self.repo_type, repo_url=self.repo_url,
                    serial=self.serial, concurrency=self.concurrency,
                    test_path=self.test_path, top_dir=self.top_dir)
                self.run_func(cmd, False, True, False, False,
                              pretty_out=False,
                              repo_type=self.repo_type,
                              repo_url=self.repo_url)
                # check that the test we're probing still failed - still
                # awkward.
                found_fail = []

                def find_fail(test_dict):
                    if test_dict['id'] == spurious_failure:
                        found_fail.append(True)

                checker = testtools.StreamToDict(find_fail)
                checker.startTestRun()
                try:
                    self.repo.get_failing().get_test().run(checker)
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
            for failure in sorted(test_conflicts):
                causes = test_conflicts[failure]
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
