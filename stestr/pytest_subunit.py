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

# This file was forked from:
# https://github.com/jogo/pytest-subunit/blob/f5da98f3bee2ffc8d898ced92034f11bcf8e35fe/pytest_subunit.py
# which itself was a fork from the now archived:
# pytest-subunit: https://github.com/lukaszo/pytest-subunit

from __future__ import annotations

from typing import Optional

import datetime
from io import StringIO
import pathlib

from _pytest._io import TerminalWriter
from _pytest.terminal import TerminalReporter
import pytest
from subunit import StreamResultToBytes


def to_path(testid: str) -> pathlib.Path:
    delim = "::"
    if delim in testid:
        path = testid.split(delim)[0]
    else:
        path = testid
    return pathlib.Path(path).resolve()


# hook
def pytest_ignore_collect(collection_path, config) -> Optional[bool]:
    # TODO(jogo): If specify a path, use same short circuit logic
    # Only collect files in the list
    if config.option.subunit_load_list:
        # TODO(jogo): memoize me
        with open(config.option.subunit_load_list) as f:
            testids = f.readlines()
        filenames = [to_path(line.strip()) for line in testids]
        for filename in filenames:
            if str(filename).startswith(str(collection_path)):
                # Don't ignore
                return None
        # Ignore everything else by default
        return True
    return None


# hook
def pytest_collection_modifyitems(session, config, items):
    if config.option.subunit:
        terminal_reporter = config.pluginmanager.getplugin("terminalreporter")
        terminal_reporter.tests_count += len(items)
    if config.option.subunit_load_list:
        with open(config.option.subunit_load_list) as f:
            to_run = f.readlines()
        to_run = [line.strip() for line in to_run]
        # print(to_run)
        # print([item.nodeid for item in items])
        filtered = [item for item in items if item.nodeid in to_run]
        items[:] = filtered


# hook
def pytest_deselected(items):
    """Update tests_count to not include deselected tests"""
    if len(items) > 0:
        pluginmanager = items[0].config.pluginmanager
        terminal_reporter = pluginmanager.getplugin("terminalreporter")
        if (
            hasattr(terminal_reporter, "tests_count")
            and terminal_reporter.tests_count > 0
        ):
            terminal_reporter.tests_count -= len(items)


# hook
def pytest_addoption(parser):
    group = parser.getgroup("terminal reporting", "reporting", after="general")
    group._addoption(
        "--subunit",
        action="store_true",
        dest="subunit",
        default=False,
        help=("enable pytest-subunit"),
    )
    group._addoption(
        "--load-list",
        dest="subunit_load_list",
        default=False,
        help=("Path to file with list of tests to run"),
    )


@pytest.mark.trylast
def pytest_configure(config):
    if config.option.subunit:
        # Get the standard terminal reporter plugin and replace it with our
        standard_reporter = config.pluginmanager.getplugin("terminalreporter")
        subunit_reporter = SubunitTerminalReporter(standard_reporter)
        config.pluginmanager.unregister(standard_reporter)
        config.pluginmanager.register(subunit_reporter, "terminalreporter")


class SubunitTerminalReporter(TerminalReporter):
    def __init__(self, reporter):
        TerminalReporter.__init__(self, reporter.config)
        self.tests_count = 0
        self.reports = []
        self.skipped = []
        self.failed = []
        self.result = StreamResultToBytes(self._tw._file)

    @property
    def no_summary(self):
        return True

    def _status(self, report: pytest.TestReport, status: str):
        # task id
        test_id = report.nodeid

        # get time
        now = datetime.datetime.now(datetime.timezone.utc)

        # capture output
        buffer = StringIO()
        writer = TerminalWriter(file=buffer)
        report.toterminal(writer)
        buffer.seek(0)
        out_bytes = buffer.read().encode("utf-8")

        # send status
        self.result.status(
            test_id=test_id,
            test_status=status,
            timestamp=now,
            file_name=report.fspath,
            file_bytes=out_bytes,
            mime_type="text/plain; charset=utf8",
        )

    def pytest_collectreport(self, report):
        pass

    def pytest_collection_finish(self, session):
        if self.config.option.collectonly:
            self._printcollecteditems(session.items)

    def pytest_collection(self):
        # Prevent shoving `collecting` message
        pass

    def report_collect(self, final=False):
        # Prevent shoving `collecting` message
        pass

    def pytest_sessionstart(self, session):
        # Set self._session
        # https://github.com/pytest-dev/pytest/blob/58cf20edf08d84c5baf08f0566cc9bccbc4ec7fd/src/_pytest/terminal.py#L692
        self._session = session

    def pytest_runtest_logstart(self, nodeid, location):
        pass

    def pytest_sessionfinish(self, session, exitstatus):
        # always exit with exitcode 0
        session.exitstatus = 0

    def pytest_runtest_logreport(self, report: pytest.TestReport):
        self.reports.append(report)
        test_id = report.nodeid
        if report.when in ["setup", "session"]:
            self._status(report, "exists")
            if report.outcome == "passed":
                self._status(report, "inprogress")
            if report.outcome == "failed":
                self._status(report, "fail")
            elif report.outcome == "skipped":
                self._status(report, "skip")
        elif report.when in ["call"]:
            if hasattr(report, "wasxfail"):
                if report.skipped:
                    self._status(report, "xfail")
                elif report.outcome == "passed":
                    self._status(report, "uxsuccess")
                    self.failed.append(test_id)
            elif report.outcome == "failed":
                self._status(report, "fail")
                self.failed.append(test_id)
            elif report.outcome == "skipped":
                self._status(report, "skip")
                self.skipped.append(test_id)
        elif report.when in ["teardown"]:
            if test_id not in self.skipped and test_id not in self.failed:
                if report.outcome == "passed":
                    self._status(report, "success")
                elif report.outcome == "failed":
                    self._status(report, "fail")
        else:
            raise Exception(str(report))

    def _printcollecteditems(self, items):
        for item in items:
            test_id = item.nodeid
            self.result.status(test_id=test_id, test_status="exists")

    def _determine_show_progress_info(self):
        # Never show progress bar
        return False
