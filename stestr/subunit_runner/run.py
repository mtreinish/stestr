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
    def __init__(self, failfast=False, tb_locals=False, stdout=sys.stdout):
        """Create a Test Runner.

        :param failfast: Stop running tests at the first failure.
        :param stdout: Output stream parameter, defaults to sys.stdout
        :param tb_locals: If set true local variables will be shown

        Either stream or stdout can be supplied, and stream will take
        precedence.
        """
        self.failfast = failfast
        self.stream = stdout
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
            print(failed_descr)
            result.status(file_name="import errors", runnable=False,
                          file_bytes=failed_descr,
                          mime_type="text/plain;charset=utf8")
            raise Exception("listing test %s errored" % test)

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


def main():
    runner = SubunitTestRunner
    program.TestProgram(
        module=None, argv=sys.argv,
        testRunner=partial(runner, stdout=sys.stdout))


if __name__ == '__main__':
    main()
