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

import faulthandler
import io
import multiprocessing
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest

import fixtures
from subunit.test_results import AutoTimingTestResultDecorator
from subunit import v2
from testtools import ExtendedToStreamDecorator

from stestr import results
from stestr import scheduler
from stestr import selection
from stestr.subunit_runner import program
from stestr.subunit_runner import run
from stestr import testlist


_DEBUG_WATCHDOG_INTERVAL = 30
# The subunit test statuses that mark the end of a test. See the
# status_mask of subunit.v2.StreamResultToBytes.
_FINAL_TEST_STATUSES = frozenset(
    ["success", "fail", "skip", "xfail", "uxsuccess"]
)


def _format_progress_duration(seconds):
    """Format a duration in seconds as a HH:MM:SS string."""
    seconds = max(int(seconds), 0)
    return "%02d:%02d:%02d" % (
        seconds // 3600,
        seconds % 3600 // 60,
        seconds % 60,
    )


def _format_dynamic_progress(tests_done, total_tests, elapsed_seconds):
    """Build the progress line displayed by the dynamic scheduler workers.

    Each worker writes the line right before running its next group of
    tests: it shows how many of the tests of the whole run already
    completed, the corresponding percentage, the elapsed time of the run
    and a rough ETA extrapolating the average duration of the completed
    tests to the remaining ones. The ETA is unknown until the first group
    of tests completes.

    :param int tests_done: The number of tests already completed by the
        run.
    :param int total_tests: The total number of tests of the run.
    :param float elapsed_seconds: Seconds elapsed since the run started.
    :return: The progress line, without a trailing newline.
    """
    tests_done = max(min(tests_done, total_tests), 0)
    percent = 100.0 * tests_done / total_tests if total_tests else 100.0
    if tests_done >= total_tests > 0:
        eta = "~00:00:00"
    elif tests_done > 0:
        eta = "~%s" % _format_progress_duration(
            elapsed_seconds / tests_done * (total_tests - tests_done)
        )
    else:
        eta = "unknown"
    return "[%d/%d (%.1f%%) elapsed: %s, ETA: %s]" % (
        tests_done,
        total_tests,
        percent,
        _format_progress_duration(elapsed_seconds),
        eta,
    )


class _DebugStreamResult:
    """StreamResult wrapper logging the per-test progress of a worker.

    It is inserted at the innermost level of the result chain built by
    _DebugSubunitTestRunner: everything is forwarded unchanged to the
    wrapped stream, and a line is written to the debug stream when a
    test starts (status in-progress) and when it reaches a final status,
    so that the state of each worker stays visible while it runs, even
    when a test never completes.
    """

    def __init__(self, result, debug_stream, worker_name):
        self._result = result
        self._debug_stream = debug_stream
        self._worker_name = worker_name
        self._start_times = {}

    def status(
        self,
        test_id=None,
        test_status=None,
        test_tags=None,
        runnable=True,
        file_name=None,
        file_bytes=None,
        eof=False,
        mime_type=None,
        route_code=None,
        timestamp=None,
    ):
        if test_status == "inprogress":
            self._start_times[test_id] = time.monotonic()
            self._write(
                "[stestr-dbg] %s START %s\n" % (self._worker_name, test_id)
            )
        elif (
            test_status in _FINAL_TEST_STATUSES
            and test_id in self._start_times
        ):
            duration = time.monotonic() - self._start_times.pop(test_id)
            self._write(
                "[stestr-dbg] %s DONE %s (%.2fs)\n"
                % (self._worker_name, test_id, duration)
            )
        self._result.status(
            test_id=test_id,
            test_status=test_status,
            test_tags=test_tags,
            runnable=runnable,
            file_name=file_name,
            file_bytes=file_bytes,
            eof=eof,
            mime_type=mime_type,
            route_code=route_code,
            timestamp=timestamp,
        )

    def _write(self, line):
        self._debug_stream.write(line)
        self._debug_stream.flush()

    def __getattr__(self, name):
        return getattr(self._result, name)


class _DebugSubunitTestRunner(run.SubunitTestRunner):
    """A SubunitTestRunner that logs per-test progress to a debug stream.

    Otherwise identical to SubunitTestRunner: the subunit stream of the
    tests is built exactly the same way, the debug lines are written to
    a separate stream (the worker's stderr in real runs).
    """

    def __init__(
        self,
        failfast=False,
        tb_locals=False,
        stdout=sys.stdout,
        debug_stream=None,
        worker_name=None,
    ):
        super().__init__(failfast=failfast, tb_locals=tb_locals, stdout=stdout)
        self._debug_stream = (
            debug_stream if debug_stream is not None else sys.stderr
        )
        self._worker_name = worker_name

    def run(self, test):
        "Run the given test case or test suite."
        result, _ = self._list(test)
        result = _DebugStreamResult(
            result, self._debug_stream, self._worker_name
        )
        result = ExtendedToStreamDecorator(result)
        result = AutoTimingTestResultDecorator(result)
        if self.failfast is not None:
            result.failfast = self.failfast
            result.tb_locals = self.tb_locals
        result.startTestRun()
        try:
            test(result)
        finally:
            result.stopTestRun()
        return result


def _dynamic_debug_watchdog(
    workers,
    groups_done,
    total_groups,
    interval=_DEBUG_WATCHDOG_INTERVAL,
    debug_stream=None,
    stop_event=None,
):
    """Report the state of a dynamic scheduler run until it ends.

    Started as a daemon thread by the dynamic scheduling mode of
    TestProcessorFixture.run_tests() when debugging is enabled. Every
    interval seconds it writes to the debug stream how many groups of
    tests were completed, how many are still pending and how many
    workers are still alive. When no group finished across two
    consecutive ticks, the still-alive workers are signaled with
    SIGUSR1 and each of them dumps its Python stack (see
    _dynamic_worker), so that a hung test can be located in the log.
    The thread returns as soon as every worker exited.

    :param workers: The list of worker dicts built by run_tests(), each
        carrying the worker process under the "proc" key.
    :param groups_done: A multiprocessing.Value incremented by each
        worker after every completed group of tests.
    :param int total_groups: The number of groups scheduled for the run.
    :param int interval: Seconds between two reports.
    :param debug_stream: The stream the reports are written to, defaults
        to sys.stderr.
    :param stop_event: A threading.Event set by the fixture cleanup to
        stop the watchdog promptly once the run ended.
    """
    if debug_stream is None:
        debug_stream = sys.stderr
    last_done = -1
    stalled_ticks = 0
    last_progress_time = time.monotonic()
    while True:
        if stop_event is not None:
            if stop_event.wait(interval):
                return
        else:
            time.sleep(interval)
        alive = []
        dead = []
        for w in workers:
            if w["proc"].is_alive():
                alive.append(w)
            else:
                dead.append(w)
        done = groups_done.value
        debug_stream.write(
            "[stestr-dbg] watchdog: groups done %s/%s, pending %s, "
            "workers alive %s/%s\n"
            % (
                done,
                total_groups,
                total_groups - done,
                len(alive),
                len(workers),
            )
        )
        if dead:
            debug_stream.write(
                "[stestr-dbg] watchdog: exited workers: %s\n"
                % ", ".join(
                    "%s (exitcode %s)" % (w["proc"].name, w["proc"].exitcode)
                    for w in dead
                )
            )
        if not alive:
            debug_stream.write(
                "[stestr-dbg] watchdog: all workers exited\n"
            )
            debug_stream.flush()
            return
        if done == last_done:
            stalled_ticks += 1
            if stalled_ticks >= 2:
                debug_stream.write(
                    "[stestr-dbg] watchdog: no group finished in %ss, "
                    "requesting a stack dump from: %s\n"
                    % (
                        int(time.monotonic() - last_progress_time),
                        ", ".join(w["proc"].name for w in alive),
                    )
                )
                debug_stream.flush()
                for w in alive:
                    try:
                        os.kill(w["proc"].pid, signal.SIGUSR1)
                    except OSError:
                        pass
        else:
            stalled_ticks = 0
            last_progress_time = time.monotonic()
        last_done = done
        debug_stream.flush()


def _dynamic_worker(
    job_queue,
    subunit_pipe,
    test_path=None,
    top_dir=None,
    debug=False,
    debug_stream=None,
    groups_done=None,
    tests_done=None,
    run_start=None,
    total_tests=0,
):
    """Run the groups of test ids from a queue until the sentinel.

    This is the target function used by the worker processes spawned for
    dynamic scheduling. Each worker pulls a single group of test ids at a
    time from the shared queue and runs it, writing the subunit output to
    the write end of a pipe that is read by the parent process. After the
    groups the parent enqueues a None sentinel per worker, and a worker
    exits as soon as it receives one. This guarantees a worker only exits
    after every group was handed to some worker, without any race on an
    empty() check between workers.

    :param job_queue: The queue with the groups of test ids to run, shared
        by all the workers of a run.
    :param subunit_pipe: The write end of the pipe used to send the
        subunit output of the tests back to the parent process.
    :param test_path: The path of the test tree. When set, the worker
        loads the whole tree with a unittest discovery first, like the
        runner subprocesses of the non-dynamic mode do, and runs the
        discovered tests matched by id. Optional.
    :param top_dir: The top level directory used by that discovery.
        Optional.
    :param bool debug: Log the progress of the worker to the debug
        stream: the groups picked from the queue and each test start
        (START) and completion (DONE), and dump the stack of the worker
        to the debug stream whenever it receives SIGUSR1 (sent by the
        watchdog of the parent process, see _dynamic_debug_watchdog).
    :param debug_stream: The stream the debug output is written to,
        defaults to sys.stderr. Only used when debug is true.
    :param groups_done: A multiprocessing.Value shared with the parent
        process, incremented after every completed group of tests.
        Optional.
    :param tests_done: A multiprocessing.Value shared with the parent
        process, incremented with the size of every completed group of
        tests. Optional.
    :param run_start: A multiprocessing.Value shared with the parent
        process, set by the parent to the time.time() at which the run
        started. Used with tests_done to display the progress of the
        run. Optional.
    :param int total_tests: The total number of tests scheduled for the
        run, used with tests_done to display the progress of the run.
    """
    # NOTE(mtreinish): Duplicate the file descriptor of the pipe so the
    # writer is decoupled from the Connection object's lifetime. Without
    # this you'll be fighting random bad file descriptor errors.
    subunit_stream = os.fdopen(os.dup(subunit_pipe.fileno()), "wb")
    parent_stdout = sys.stdout
    # The non-dynamic mode loads the test ids from a subprocess started
    # with python -m which puts the current working directory on sys.path.
    # Do the same here so the tests of the project under test are
    # importable by name in the worker.
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
    # The non-dynamic runner subprocess is started with
    # `python -m stestr.subunit_runner.run`, so sys.argv[0] is the path of
    # the run module. Some projects derive names from it, e.g. the
    # iptables filter chains of Neutron, so present the same value here.
    sys.argv = [run.__file__]
    # Point the worker's stdout at the subunit stream (buffered text, the
    # same as what a subprocess runner gets) so that any output the tests
    # write is captured in the subunit stream instead of leaking into the
    # parent's console.
    sys.stdout = io.TextIOWrapper(subunit_stream)
    if debug:
        if debug_stream is None:
            debug_stream = sys.stderr
        # NOTE: The dump handler replaces any handler registered before
        # (e.g. by the code of the project under test at discovery time)
        # and does not chain to it: the worker must keep running after a
        # dump, since a slow test must not be killed by it.
        faulthandler.register(
            signal.SIGUSR1, file=debug_stream, all_threads=True
        )
        worker_name = multiprocessing.current_process().name
        picked_groups = 0
    try:
        test_map = {}
        if test_path:
            # The non-dynamic mode runs the tests of a worker from a
            # subprocess that loads the whole test tree through a unittest
            # discovery and then filters it by the test ids. Mirror it
            # here, so that a worker starts with the same loaded state as
            # a non-dynamic runner: some projects rely on those import
            # side effects, e.g. test models that register into a shared
            # sqlalchemy metadata when their module is imported, and
            # without them the tables of those models are never created
            # in the test databases. It also gives the actual test
            # objects to run, matched by id: the unittest name loader
            # cannot resolve the ids generated dynamically by ddt.
            discovered = unittest.defaultTestLoader.discover(
                test_path, top_level_dir=top_dir
            )
            for test in program.iterate_tests(discovered):
                test_map[test.id()] = test

        def _count_tests_done(count):
            # Add the size of a completed group to the shared counter of
            # the run. Returns True when the whole run is completed, so
            # that the caller displays the final progress line.
            if tests_done is None or not total_tests:
                return False
            with tests_done.get_lock():
                tests_done.value += count
                return tests_done.value >= total_tests

        def _write_progress_line(tests_done_value):
            elapsed = max(time.time() - run_start.value, 0.0)
            sys.stderr.write(
                "%s\n"
                % _format_dynamic_progress(
                    tests_done_value, total_tests, elapsed
                )
            )
            sys.stderr.flush()

        while True:
            group = job_queue.get()
            if group is None:
                break
            # Display the completion of the run on stderr before running
            # the next group of tests.
            if (
                tests_done is not None
                and run_start is not None
                and total_tests
            ):
                with tests_done.get_lock():
                    done = tests_done.value
                _write_progress_line(done)
            if debug:
                picked_groups += 1
                debug_stream.write(
                    "[stestr-dbg] %s picked group #%s (%s tests)\n"
                    % (worker_name, picked_groups, len(group))
                )
                debug_stream.flush()
            if test_path:
                tests = [
                    test_map[test_id] for test_id in group if test_id in test_map
                ]
                if not tests:
                    # The whole group was filtered out: count it as done
                    # anyway so that the accounting of the parent stays
                    # right.
                    if groups_done is not None:
                        with groups_done.get_lock():
                            groups_done.value += 1
                    if _count_tests_done(len(group)):
                        _write_progress_line(tests_done.value)
                    continue
            else:
                tests = [
                    unittest.defaultTestLoader.loadTestsFromName(test_id)
                    for test_id in group
                ]
            # Run the group as a single suite, so that the class level
            # fixtures are handled by the suite like in the non-dynamic
            # mode.
            if debug:
                runner = _DebugSubunitTestRunner(
                    stdout=sys.stdout,
                    debug_stream=debug_stream,
                    worker_name=worker_name,
                )
            else:
                runner = run.SubunitTestRunner(stdout=sys.stdout)
            runner.run(unittest.TestSuite(tests))
            if groups_done is not None:
                with groups_done.get_lock():
                    groups_done.value += 1
            if _count_tests_done(len(group)):
                _write_progress_line(tests_done.value)
    finally:
        sys.stdout.flush()
        subunit_stream.close()
        sys.stdout = parent_stdout


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
    :param path exclude_list: Path to an exclusion list file, this file
        contains a separate regex exclude on each newline.
    :param path include_list: Path to an inclusion list file, this file
         contains a separate regex on each newline.
    :param boolean randomize: Randomize the test order after they are
        partitioned into separate workers
    :param bool dynamic: Use the experimental dynamic scheduler, workers
        will ask for the next test to run instead of being assigned a
        partition up front. Each worker also displays the completion of
        the run (tests done, percentage, elapsed time and a rough ETA)
        on stderr right before running its next group of tests.
    :param bool dynamic_debug: Enable the debug output of the dynamic
        scheduler (see the --dynamic-debug option of stestr run): each
        worker logs its progress to stderr and a watchdog thread
        reports the state of the run until it ends. Only used when
        dynamic is true.
    :param str test_path: The path of the test tree, used by the dynamic
        scheduler to run a full discovery in each worker, mirroring the
        non-dynamic runner subprocesses. Optional.
    :param str top_dir: The top level directory of the project, used
        together with test_path by the dynamic scheduler. Optional.
    """

    def __init__(
        self,
        test_ids,
        cmd_template,
        listopt,
        idoption,
        repository,
        parallel=True,
        listpath=None,
        test_filters=None,
        group_callback=None,
        serial=False,
        worker_path=None,
        concurrency=0,
        exclude_list=None,
        exclude_regex=None,
        include_list=None,
        randomize=False,
        dynamic=False,
        dynamic_debug=False,
        test_path=None,
        top_dir=None,
    ):
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
        self.exclude_list = exclude_list
        self.include_list = include_list
        self.exclude_regex = exclude_regex
        self.randomize = randomize
        self.dynamic = dynamic
        self.dynamic_debug = dynamic_debug
        self._debug_stop = None
        self.test_path = test_path
        self.top_dir = top_dir

    def setUp(self):
        super().setUp()
        variable_regex = r"\$(IDOPTION|IDFILE|IDLIST|LISTOPT)"
        variables = {}
        list_variables = {"LISTOPT": self.listopt}
        cmd = self.template
        default_idstr = None

        def list_subst(match):
            return list_variables.get(match.groups(1)[0], "")

        self.list_cmd = re.sub(variable_regex, list_subst, cmd)
        nonparallel = not self.parallel
        selection_logic = (
            self.test_filters
            or self.exclude_list
            or self.include_list
            or self.exclude_regex
        )
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
            name = ""
            idlist = ""
        else:
            self.test_ids = selection.construct_list(
                self.test_ids,
                exclude_list=self.exclude_list,
                include_list=self.include_list,
                regexes=self.test_filters,
                exclude_regex=self.exclude_regex,
            )
            name = self.make_listfile()
            variables["IDFILE"] = name
            idlist = " ".join(self.test_ids)
        variables["IDLIST"] = idlist

        def subst(match):
            return variables.get(match.groups(1)[0], "")

        if self.test_ids is None:
            # No test ids, no id option.
            idoption = ""
        else:
            idoption = re.sub(variable_regex, subst, self.idoption)
            variables["IDOPTION"] = idoption
        self.cmd = re.sub(variable_regex, subst, cmd)

    def make_listfile(self):
        name = None
        try:
            if self._listpath:
                name = self._listpath
                stream = open(name, "wb")
            else:
                fd, name = tempfile.mkstemp()
                stream = os.fdopen(fd, "wb")
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
        preexec_fn = None if sys.platform == "win32" else self._clear_SIGPIPE
        return subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            preexec_fn=preexec_fn,
        )

    def list_tests(self):
        """List the tests returned by list_cmd.

        :return: A list of test ids.
        """
        run_proc = self._start_process(self.list_cmd)
        out, err = run_proc.communicate()
        if run_proc.returncode != 0:
            sys.stdout.write(
                "\n=========================\n"
                "Failures during discovery"
                "\n=========================\n"
            )
            new_out = io.BytesIO()
            v2.ByteStreamToStreamResult(io.BytesIO(out), "stdout").run(
                results.CatFiles(new_out)
            )
            out = new_out.getvalue()
            if out:
                sys.stdout.write(out.decode("utf8"))
            if err:
                sys.stderr.write(err.decode("utf8"))
            sys.stdout.write(
                "\n" + "=" * 80 + "\n"
                "The above traceback was encountered during "
                "test discovery which imports all the found test"
                " modules in the specified test_path.\n"
            )
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
                test_ids,
                self.worker_path,
                self.repository,
                self._group_callback,
                self.randomize,
            )
        # If we have multiple workers partition the tests and recursively
        # create single worker TestProcessorFixtures for each worker
        else:
            test_id_groups = scheduler.partition_tests(
                test_ids, self.concurrency, self.repository, self._group_callback
            )
        if not self.dynamic:
            for test_ids in test_id_groups:
                if not test_ids:
                    # No tests in this partition
                    continue
                fixture = self.useFixture(
                    TestProcessorFixture(
                        test_ids,
                        self.template,
                        self.listopt,
                        self.idoption,
                        self.repository,
                        parallel=False,
                    )
                )
                result.extend(fixture.run_tests())
            return result
        else:
            test_id_list = scheduler.get_dynamic_test_list(
                test_ids, self.repository, self._group_callback
            )
            if not test_id_list:
                # Nothing to run, return an empty list of processes so the
                # caller can report that nothing matched.
                return result
            # Use spawn to launch a fresh interpreter and have the minimal
            # amount of state from stestr when invoking the test runner.
            # This is equivalent to non-dynamic mode using subprocess instead
            # of multiprocessing.
            context = multiprocessing.get_context("spawn")
            # NOTE(mtreinish): The queue is scoped to the instance so it
            # stays alive as long as the fixture does. If it was garbage
            # collected while the workers are still running, the finalizer
            # of its internal locks would unlink the underlying semaphores
            # and any worker that is still starting would crash with a
            # FileNotFoundError when rebuilding the queue.
            self._test_list_queue = context.Queue()

            for group in test_id_list:
                self._test_list_queue.put(group)
            # Enqueue a sentinel per worker. A worker exits when it receives
            # a sentinel, so every worker exits only after all the test ids
            # were handed to a worker.
            for _ in range(self.concurrency):
                self._test_list_queue.put(None)

            groups_done = None
            if self.dynamic_debug:
                groups_done = context.Value("i", 0)
            # The progress display counts completed tests in a shared
            # counter, and reads the start time of the run from a shared
            # value set by the parent before spawning the workers. Both
            # are scoped to the instance like the queue above: if they
            # were garbage collected while the workers are still
            # starting, the finalizer of their locks would unlink the
            # underlying semaphores and the workers would crash with a
            # FileNotFoundError when rebuilding them.
            tests_done = context.Value("i", 0)
            run_start = context.Value("d", time.time())
            total_tests = sum(len(group) for group in test_id_list)
            self._tests_done = tests_done
            self._run_start = run_start
            self._total_tests = total_tests
            for i in range(self.concurrency):
                fd_pipe_r, fd_pipe_w = context.Pipe(False)
                proc = context.Process(
                    target=_dynamic_worker,
                    name="worker-%s" % i,
                    args=(
                        self._test_list_queue,
                        fd_pipe_w,
                        self.test_path,
                        self.top_dir,
                        self.dynamic_debug,
                        None,
                        groups_done,
                        tests_done,
                        run_start,
                        total_tests,
                    ),
                )
                proc.start()
                # The parent never writes to the pipe. Close its write end
                # immediately so the reader sees EOF as soon as the workers
                # exit instead of only when the parent cleans up.
                fd_pipe_w.close()
                stream_read = os.dup(fd_pipe_r.fileno())
                fd_pipe_r.close()
                result.append({"stream": stream_read, "proc": proc})
            if self.dynamic_debug:
                self._debug_stop = threading.Event()
                # Stop the watchdog as soon as the fixture is cleaned up,
                # so that it does not report one last time long after the
                # end of the run.
                self.addCleanup(self._debug_stop.set)
                threading.Thread(
                    target=_dynamic_debug_watchdog,
                    args=(result, groups_done, len(test_id_list)),
                    kwargs={"stop_event": self._debug_stop},
                    name="stestr-dynamic-debug-watchdog",
                    daemon=True,
                ).start()
            return result
