# Copyright 2019 Matthew Treinish
# Copyright (C) Jelmer Vernooij <jelmer@samba.org> 2007
#
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

from functools import partial
import os
import sys

from subunit import StreamResultToBytes
from subunit.test_results import AutoTimingTestResultDecorator
from testtools import ExtendedToStreamDecorator

from stestr.subunit_runner import program


class SubunitTestRunner(object):
    def __init__(self, verbosity=None, failfast=None, buffer=None,
                 stream=None, stdout=None, tb_locals=False):
        """Create a Test Runner.

        :param verbosity: Ignored.
        :param failfast: Stop running tests at the first failure.
        :param buffer: Ignored.
        :param stream: Upstream unittest stream parameter.
        :param stdout: Testtools stream parameter.
        :param tb_locals: Testtools traceback in locals parameter.

        Either stream or stdout can be supplied, and stream will take
        precedence.
        """
        self.failfast = failfast
        self.stream = stream or stdout or sys.stdout
        self.tb_locals = tb_locals

    def run(self, test):
        "Run the given test case or test suite."
        result, _ = self._list(test)
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

    def list(self, test, loader=None):
        "List the test."
        result, errors = self._list(test)
        if loader is not None:
            errors = loader.errors
        if errors:
            failed_descr = '\n'.join(errors).encode('utf8')
            result.status(file_name="import errors", runnable=False,
                          file_bytes=failed_descr,
                          mime_type="text/plain;charset=utf8")
            sys.exit(2)

    def _list(self, test):
        test_ids, errors = program.list_test(test)
        try:
            fileno = self.stream.fileno()
        except Exception:
            fileno = None
        if fileno is not None:
            stream = os.fdopen(fileno, 'wb', 0)
        else:
            stream = self.stream
        result = StreamResultToBytes(stream)
        for test_id in test_ids:
            result.status(test_id=test_id, test_status='exists')
        return result, errors


class SubunitTestProgram(program.TestProgram):

    USAGE = program.USAGE_AS_MAIN

    def usageExit(self, msg=None):
        if msg:
            print(msg)
        usage = {'progName': self.progName, 'catchbreak': '', 'failfast': '',
                 'buffer': ''}
        if self.failfast is not False:
            usage['failfast'] = program.FAILFAST
        if self.catchbreak is not False:
            usage['catchbreak'] = program.CATCHBREAK
        if self.buffer is not False:
            usage['buffer'] = program.BUFFEROUTPUT
        usage_text = self.USAGE % usage
        usage_lines = usage_text.split('\n')
        usage_lines.insert(2, "Run a test suite with a subunit reporter.")
        usage_lines.insert(3, "")
        print('\n'.join(usage_lines))
        sys.exit(2)


def main():
    runner = SubunitTestRunner
    if sys.version_info[0] >= 3:
        SubunitTestProgram(
            module=None, argv=sys.argv,
            testRunner=partial(runner, stdout=sys.stdout),
            exit=False)
    else:
        from testtools import run as testtools_run
        testtools_run.TestProgram(module=None, argv=sys.argv,
                                  testRunner=runner,
                                  stdout=sys.stdout, exit=False)


if __name__ == '__main__':
    main()
