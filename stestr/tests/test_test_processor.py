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

import io
import multiprocessing
import os
import queue
import signal
import subprocess
import threading
import time
import unittest
from unittest import mock

import fixtures
import subunit
import testtools

from stestr import test_processor
from stestr.tests import base


class TestTestProcessorFixture(base.TestCase):
    def setUp(self):
        super().setUp()
        self._fixture = test_processor.TestProcessorFixture(
            mock.sentinel.test_ids,
            mock.sentinel.options,
            mock.sentinel.cmd_template,
            mock.sentinel.listopt,
            mock.sentinel.idoption,
            mock.sentinel.repository,
        )

    @mock.patch.object(subprocess, "Popen")
    @mock.patch.object(test_processor, "sys")
    def _check_start_process(
        self, mock_sys, mock_Popen, platform="win32", expected_fn=None
    ):
        mock_sys.platform = platform

        self._fixture._start_process(mock.sentinel.cmd)

        mock_Popen.assert_called_once_with(
            mock.sentinel.cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            preexec_fn=expected_fn,
        )

    def test_start_process_win32(self):
        self._check_start_process()

    def test_start_process_linux(self):
        self._check_start_process(
            platform="linux2", expected_fn=self._fixture._clear_SIGPIPE
        )


def _parse_subunit_output(raw):
    case = subunit.ByteStreamToStreamResult(io.BytesIO(raw))
    tests = []

    def _add_test(test):
        tests.append(test)

    outcomes = testtools.StreamToDict(_add_test)
    result = testtools.CopyStreamResult([testtools.StreamResult(), outcomes])
    result.startTestRun()
    try:
        case.run(result)
    finally:
        result.stopTestRun()
    return tests


def _read_connection_output(read_conn):
    chunks = []
    while True:
        try:
            chunk = os.read(read_conn.fileno(), 65536)
        except OSError:
            break
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


class _FakeTestCase(unittest.TestCase):
    def test_fake(self):
        pass


class TestDebugStreamResult(base.TestCase):
    _test_id = "stestr.tests.test_test_processor._FakeTestCase.test_fake"

    def test_start_and_done_logged(self):
        debug_stream = io.StringIO()
        subunit_stream = io.BytesIO()
        runner = test_processor._DebugSubunitTestRunner(
            stdout=subunit_stream,
            debug_stream=debug_stream,
            worker_name="worker-0",
        )
        runner.run(unittest.TestSuite([_FakeTestCase("test_fake")]))
        self.assertIn(
            "[stestr-dbg] worker-0 START %s\n" % self._test_id,
            debug_stream.getvalue(),
        )
        self.assertIn(
            "[stestr-dbg] worker-0 DONE %s (" % self._test_id,
            debug_stream.getvalue(),
        )
        # The subunit stream must keep carrying the result of the tests.
        tests = _parse_subunit_output(subunit_stream.getvalue())
        statuses = {test["id"]: test["status"] for test in tests}
        self.assertEqual("success", statuses[self._test_id])


class TestDynamicWorkerDebug(base.TestCase):
    _test_id = "stestr.tests.test_test_processor._FakeTestCase.test_fake"

    def _make_pipe(self):
        ctx = multiprocessing.get_context("spawn")
        return ctx.Pipe(False)

    def test_worker_logs_progress_and_counts_groups(self):
        read_conn, write_conn = self._make_pipe()
        debug_stream = io.StringIO()
        groups_done = multiprocessing.Value("i", 0)
        job_queue = queue.Queue()
        job_queue.put([self._test_id])
        job_queue.put(None)
        with mock.patch.object(test_processor.faulthandler, "register"):
            test_processor._dynamic_worker(
                job_queue,
                write_conn,
                debug=True,
                debug_stream=debug_stream,
                groups_done=groups_done,
            )
        write_conn.close()
        out = _read_connection_output(read_conn)
        debug_out = debug_stream.getvalue()
        self.assertEqual(1, groups_done.value)
        self.assertIn("picked group #1 (1 tests)", debug_out)
        self.assertIn("START %s\n" % self._test_id, debug_out)
        self.assertIn("DONE %s (" % self._test_id, debug_out)
        # The result of the test still goes to the subunit pipe.
        tests = _parse_subunit_output(out)
        statuses = {test["id"]: test["status"] for test in tests}
        self.assertEqual("success", statuses[self._test_id])

    def test_filtered_out_group_counted_as_done(self):
        top_dir = self.useFixture(fixtures.TempDir()).path
        user_test = os.path.join(top_dir, "test_user.py")
        with open(user_test, "w") as f:
            f.write(
                "import unittest\n"
                "\n"
                "\n"
                "class TestDiscoverySeeding(unittest.TestCase):\n"
                "    def test_here(self):\n"
                "        pass\n"
            )
        read_conn, write_conn = self._make_pipe()
        debug_stream = io.StringIO()
        groups_done = multiprocessing.Value("i", 0)
        job_queue = queue.Queue()
        job_queue.put(["test_user.TestDiscoverySeeding.test_missing"])
        job_queue.put(None)
        with mock.patch.object(test_processor.faulthandler, "register"):
            test_processor._dynamic_worker(
                job_queue,
                write_conn,
                test_path=top_dir,
                top_dir=top_dir,
                debug=True,
                debug_stream=debug_stream,
                groups_done=groups_done,
            )
        write_conn.close()
        out = _read_connection_output(read_conn)
        debug_out = debug_stream.getvalue()
        # A group whose tests were all filtered out must still be counted
        # as done, so that the accounting of the parent stays right.
        self.assertEqual(1, groups_done.value)
        self.assertIn("picked group #1 (1 tests)", debug_out)
        self.assertNotIn("START", debug_out)
        self.assertEqual(b"", out)

    def test_filtered_out_group_counts_tests_done(self):
        # The test ids of a group filtered out entirely still count as
        # done for the progress display, like they do for the debug
        # watchdog counter.
        top_dir = self.useFixture(fixtures.TempDir()).path
        user_test = os.path.join(top_dir, "test_user.py")
        with open(user_test, "w") as f:
            f.write(
                "import unittest\n"
                "\n"
                "\n"
                "class TestDiscoverySeeding(unittest.TestCase):\n"
                "    def test_here(self):\n"
                "        pass\n"
            )
        read_conn, write_conn = self._make_pipe()
        debug_stream = io.StringIO()
        stderr = io.StringIO()
        tests_done = multiprocessing.Value("i", 0)
        run_start = multiprocessing.Value("d", time.time())
        job_queue = queue.Queue()
        job_queue.put(["test_user.TestDiscoverySeeding.test_missing"])
        job_queue.put(None)
        with mock.patch.object(test_processor.sys, "stderr", stderr):
            with mock.patch.object(test_processor.faulthandler, "register"):
                test_processor._dynamic_worker(
                    job_queue,
                    write_conn,
                    test_path=top_dir,
                    top_dir=top_dir,
                    debug=True,
                    debug_stream=debug_stream,
                    tests_done=tests_done,
                    run_start=run_start,
                    total_tests=1,
                )
        write_conn.close()
        self.assertEqual(1, tests_done.value)
        self.assertIn(
            "[1/1 (100.0%) elapsed: 00:00:00, ETA: ~00:00:00]",
            stderr.getvalue(),
        )


class _FakeWorkerProc:
    def __init__(self, name, pid, ticks_alive, exitcode=None, on_tick=None):
        self.name = name
        self.pid = pid
        self.exitcode = exitcode
        self._ticks = 0
        self._ticks_alive = ticks_alive
        self._on_tick = on_tick

    def is_alive(self):
        self._ticks += 1
        if self._on_tick:
            self._on_tick(self._ticks)
        return self._ticks <= self._ticks_alive


class _FakeCounter:
    def __init__(self, value=0):
        self.value = value


class TestDynamicDebugWatchdog(base.TestCase):
    def test_watchdog_dumps_stacks_after_two_stalled_ticks(self):
        debug_stream = io.StringIO()
        counter = _FakeCounter(0)
        proc = _FakeWorkerProc("worker-0", 4242, 3)
        with mock.patch("os.kill") as kill:
            test_processor._dynamic_debug_watchdog(
                [{"proc": proc}],
                counter,
                1,
                interval=0.01,
                debug_stream=debug_stream,
            )
        out = debug_stream.getvalue()
        self.assertIn("groups done 0/1, pending 1, workers alive 1/1", out)
        self.assertIn("no group finished in", out)
        self.assertIn("worker-0", out)
        kill.assert_called_once_with(4242, signal.SIGUSR1)

    def test_watchdog_resets_stall_when_groups_finish(self):
        debug_stream = io.StringIO()
        counter = _FakeCounter(0)

        # The counter is bumped when the second tick starts, as if a
        # group of tests finished in between.
        def bump_on_tick(tick):
            if tick == 2:
                counter.value = 1

        proc = _FakeWorkerProc("worker-0", 4242, 4, on_tick=bump_on_tick)
        with mock.patch("os.kill") as kill:
            test_processor._dynamic_debug_watchdog(
                [{"proc": proc}],
                counter,
                2,
                interval=0.01,
                debug_stream=debug_stream,
            )
        out = debug_stream.getvalue()
        self.assertIn("groups done 0/2", out)
        self.assertIn("groups done 1/2", out)
        self.assertEqual(1, out.count("no group finished in"))
        kill.assert_called_once_with(4242, signal.SIGUSR1)

    def test_watchdog_stops_when_all_workers_exit(self):
        debug_stream = io.StringIO()
        counter = _FakeCounter(0)
        proc = _FakeWorkerProc("worker-0", 4242, 0, exitcode=1)
        with mock.patch("os.kill") as kill:
            test_processor._dynamic_debug_watchdog(
                [{"proc": proc}],
                counter,
                1,
                interval=0.01,
                debug_stream=debug_stream,
            )
        out = debug_stream.getvalue()
        self.assertIn("exited workers: worker-0 (exitcode 1)", out)
        self.assertIn("all workers exited", out)
        kill.assert_not_called()


class TestDynamicProgressFormat(base.TestCase):
    def test_format_before_first_completion(self):
        # The ETA is unknown until a first group of tests completed.
        self.assertEqual(
            "[0/312 (0.0%) elapsed: 00:01:23, ETA: unknown]",
            test_processor._format_dynamic_progress(0, 312, 83),
        )

    def test_format_mid_run(self):
        # 42 done tests over 312, 83s elapsed: the ETA extrapolates the
        # average duration of the done tests to the 270 remaining ones.
        self.assertEqual(
            "[42/312 (13.5%) elapsed: 00:01:23, ETA: ~00:08:53]",
            test_processor._format_dynamic_progress(42, 312, 83),
        )

    def test_format_completion(self):
        self.assertEqual(
            "[312/312 (100.0%) elapsed: 00:10:00, ETA: ~00:00:00]",
            test_processor._format_dynamic_progress(312, 312, 600),
        )

    def test_format_rounds_the_percentage(self):
        self.assertEqual(
            "[1/3 (33.3%) elapsed: 00:00:09, ETA: ~00:00:18]",
            test_processor._format_dynamic_progress(1, 3, 9),
        )

    def test_format_clamps_out_of_range_counts(self):
        # A worker may run fewer tests than its group contains when the
        # test ids cannot all be loaded; the display never goes out of
        # range.
        self.assertEqual(
            "[3/3 (100.0%) elapsed: 00:00:30, ETA: ~00:00:00]",
            test_processor._format_dynamic_progress(5, 3, 30),
        )
        self.assertEqual(
            "[0/3 (0.0%) elapsed: 00:00:30, ETA: unknown]",
            test_processor._format_dynamic_progress(-1, 3, 30),
        )


class TestDynamicWorker(base.TestCase):
    # A stable, importable test id from this module used to exercise the
    # worker without spawning processes.
    _test_id = (
        "stestr.tests.test_test_processor"
        ".TestTestProcessorFixture.test_start_process_linux"
    )

    def _run_worker(self, job_queue):
        ctx = multiprocessing.get_context("spawn")
        read_conn, write_conn = ctx.Pipe(False)
        test_processor._dynamic_worker(job_queue, write_conn)
        write_conn.close()
        return _read_connection_output(read_conn)

    def test_dynamic_worker_exits_on_sentinel(self):
        job_queue = queue.Queue()
        job_queue.put(None)
        out = self._run_worker(job_queue)
        self.assertEqual(b"", out)

    def test_dynamic_worker_runs_queued_tests(self):
        job_queue = queue.Queue()
        job_queue.put([self._test_id])
        job_queue.put(None)
        out = self._run_worker(job_queue)
        tests = _parse_subunit_output(out)
        statuses = {test["id"]: test["status"] for test in tests}
        self.assertIn(self._test_id, statuses)
        self.assertEqual("success", statuses[self._test_id])

    def test_dynamic_worker_sentinel_after_tests(self):
        # A worker must exit cleanly when it receives the sentinel, even if
        # other workers already consumed part of the queue.
        job_queue = queue.Queue()
        for _ in range(3):
            job_queue.put(None)
        out = self._run_worker(job_queue)
        self.assertEqual(b"", out)

    def test_worker_reports_progress_and_counts_tests(self):
        job_queue = queue.Queue()
        job_queue.put([self._test_id])
        job_queue.put([self._test_id])
        job_queue.put(None)
        read_conn, write_conn = multiprocessing.get_context("spawn").Pipe(
            False
        )
        tests_done = multiprocessing.Value("i", 0)
        run_start = multiprocessing.Value("d", time.time())
        stderr = io.StringIO()
        with mock.patch.object(test_processor.sys, "stderr", stderr):
            test_processor._dynamic_worker(
                job_queue,
                write_conn,
                tests_done=tests_done,
                run_start=run_start,
                total_tests=2,
            )
        write_conn.close()
        read_conn.close()
        # Each completed group of tests counts its test ids in the
        # shared counter.
        self.assertEqual(2, tests_done.value)
        out = stderr.getvalue()
        # A progress line is displayed before each group of tests runs.
        self.assertIn(
            "[0/2 (0.0%) elapsed: 00:00:00, ETA: unknown]\n", out
        )
        self.assertIn(
            "[1/2 (50.0%) elapsed: 00:00:00, ETA: ~00:00:00]\n", out
        )
        # And the completion of the whole run is displayed once at the
        # end, by the worker that ran the last group.
        self.assertIn(
            "[2/2 (100.0%) elapsed: 00:00:00, ETA: ~00:00:00]\n", out
        )

    def test_worker_without_counters_does_not_display_progress(self):
        # The progress display is driven by the counters shared with the
        # parent: a worker without them (e.g. a direct worker call in a
        # test) stays silent.
        job_queue = queue.Queue()
        job_queue.put([self._test_id])
        job_queue.put(None)
        read_conn, write_conn = multiprocessing.get_context("spawn").Pipe(
            False
        )
        stderr = io.StringIO()
        with mock.patch.object(test_processor.sys, "stderr", stderr):
            test_processor._dynamic_worker(
                job_queue,
                write_conn,
            )
        write_conn.close()
        read_conn.close()
        self.assertEqual("", stderr.getvalue())


class TestProcessorDynamicRun(base.TestCase):
    _test_id = (
        "stestr.tests.test_test_processor"
        ".TestTestProcessorFixture.test_start_process_linux"
    )

    def _get_dynamic_fixture(
        self, test_ids, concurrency=2, dynamic_debug=False
    ):
        fixture = test_processor.TestProcessorFixture(
            test_ids,
            "python -m stestr.subunit_runner.run $IDOPTION",
            "--list",
            "--load-list $IDFILE",
            None,
            concurrency=concurrency,
            dynamic=True,
            dynamic_debug=dynamic_debug,
        )
        return self.useFixture(fixture)

    def test_dynamic_run_tests_returns_worker_dicts(self):
        fixture = self._get_dynamic_fixture([self._test_id])
        workers = fixture.run_tests()
        self.assertEqual(2, len(workers))
        outputs = []
        for worker in workers:
            self.assertIn("stream", worker)
            self.assertIn("proc", worker)
            worker["proc"].join()
            self.assertEqual(0, worker["proc"].exitcode)
            with os.fdopen(worker["stream"], "rb") as stream:
                outputs.append(stream.read())
        tests = _parse_subunit_output(b"".join(outputs))
        statuses = {test["id"]: test["status"] for test in tests}
        self.assertIn(self._test_id, statuses)
        self.assertEqual("success", statuses[self._test_id])

    def test_dynamic_run_tests_progress_display(self):
        # Every worker displays the completion of the whole run on stderr
        # right before running its next group of tests.
        fixture = self._get_dynamic_fixture([self._test_id])
        tmpdir = self.useFixture(fixtures.TempDir()).path
        stderr_path = os.path.join(tmpdir, "workers_stderr")
        with open(stderr_path, "wb") as stderr_file:
            stderr_fd = os.dup(2)
            os.dup2(stderr_file.fileno(), 2)
            try:
                workers = fixture.run_tests()
                for worker in workers:
                    worker["proc"].join()
                    self.assertEqual(0, worker["proc"].exitcode)
            finally:
                os.dup2(stderr_fd, 2)
                os.close(stderr_fd)
        with open(stderr_path) as stderr_file:
            stderr_out = stderr_file.read()
        self.assertIn("[0/1 (0.0%) elapsed:", stderr_out)
        self.assertIn("[1/1 (100.0%)", stderr_out)
        self.assertEqual(1, fixture._tests_done.value)
        fixture = self._get_dynamic_fixture([])
        workers = fixture.run_tests()
        self.assertEqual([], workers)

    def test_dynamic_debug_run_tests(self):
        fixture = self._get_dynamic_fixture(
            [self._test_id], concurrency=2, dynamic_debug=True
        )
        # The debug output of the workers goes to the inherited stderr:
        # redirect it while the workers live, so that it does not
        # pollute the output of the stestr suite itself.
        stderr_fd = os.dup(2)
        with open(os.devnull, "wb") as devnull:
            os.dup2(devnull.fileno(), 2)
            try:
                workers = fixture.run_tests()
                outputs = []
                for worker in workers:
                    worker["proc"].join()
                    self.assertEqual(0, worker["proc"].exitcode)
                    with os.fdopen(worker["stream"], "rb") as stream:
                        outputs.append(stream.read())
            finally:
                os.dup2(stderr_fd, 2)
                os.close(stderr_fd)
        self.assertTrue(
            any(
                thread.name == "stestr-dynamic-debug-watchdog"
                for thread in threading.enumerate()
            )
        )
        tests = _parse_subunit_output(b"".join(outputs))
        statuses = {test["id"]: test["status"] for test in tests}
        self.assertIn(self._test_id, statuses)
        self.assertEqual("success", statuses[self._test_id])


class TestDynamicDiscoverySeeding(base.TestCase):
    def test_worker_discovers_test_tree_before_running(self):
        # The dynamic workers must import the whole test tree the same way
        # the non-dynamic runner subprocesses do, because projects rely on
        # the import side effects of the test modules (e.g. test models
        # registering into a shared sqlalchemy metadata at import time).
        top_dir = self.useFixture(fixtures.TempDir()).path
        side_effect = os.path.join(top_dir, "test_side_effect.py")
        with open(side_effect, "w") as f:
            f.write(
                "import os\n"
                "with open(os.path.join(os.path.dirname(__file__), "
                "'marker'), 'w') as marker:\n"
                "    marker.write('discovered')\n"
            )
        user_test = os.path.join(top_dir, "test_user.py")
        with open(user_test, "w") as f:
            f.write(
                "import os\n"
                "import unittest\n"
                "\n"
                "\n"
                "class TestDiscoverySeeding(unittest.TestCase):\n"
                "    def test_side_effect_ran(self):\n"
                "        marker = os.path.join(\n"
                "            os.path.dirname(__file__), 'marker')\n"
                "        self.assertTrue(os.path.exists(marker))\n"
            )
        fixture = test_processor.TestProcessorFixture(
            ["test_user.TestDiscoverySeeding.test_side_effect_ran"],
            "python -m stestr.subunit_runner.run $IDOPTION",
            "--list",
            "--load-list $IDFILE",
            None,
            concurrency=2,
            dynamic=True,
            test_path=top_dir,
            top_dir=top_dir,
        )
        self.useFixture(fixture)
        workers = fixture.run_tests()
        outputs = []
        for worker in workers:
            worker["proc"].join()
            self.assertEqual(0, worker["proc"].exitcode)
            with os.fdopen(worker["stream"], "rb") as stream:
                outputs.append(stream.read())
        tests = _parse_subunit_output(b"".join(outputs))
        statuses = {test["id"]: test["status"] for test in tests}
        self.assertEqual(
            "success",
            statuses["test_user.TestDiscoverySeeding.test_side_effect_ran"],
        )
