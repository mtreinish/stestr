# Copyright 2019 Matthew Treinish
# Copyright (c) 2009 testtools developers.
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

import functools
import os
import sys
import unittest

import extras


def filter_by_ids(suite_or_case, test_ids):
    """Remove tests from suite_or_case where their id is not in test_ids.

    :param suite_or_case: A test suite or test case.
    :param test_ids: Something that supports the __contains__ protocol.
    :return: suite_or_case, unless suite_or_case was a case that itself
        fails the predicate when it will return a new unittest.TestSuite with
        no contents.

    For subclasses of TestSuite, filtering is done by:
        - attempting to call suite.filter_by_ids(test_ids)
        - if there is no method, iterating the suite and identifying tests to
          remove, then removing them from _tests, manually recursing into
          each entry.

    For objects with an id() method - TestCases, filtering is done by:
        - attempting to return case.filter_by_ids(test_ids)
        - if there is no such method, checking for case.id() in test_ids
          and returning case if it is, or TestSuite() if it is not.

    For anything else, it is not filtered - it is returned as-is.

    To provide compatibility with this routine for a custom TestSuite, just
    define a filter_by_ids() method that will return a TestSuite equivalent to
    the original minus any tests not in test_ids.
    Similarly to provide compatibility for a custom TestCase that does
    something unusual define filter_by_ids to return a new TestCase object
    that will only run test_ids that are in the provided container. If none
    would run, return an empty TestSuite().

    The contract for this function does not require mutation - each filtered
    object can choose to return a new object with the filtered tests. However
    because existing custom TestSuite classes in the wild do not have this
    method, we need a way to copy their state correctly which is tricky:
    thus the backwards-compatible code paths attempt to mutate in place rather
    than guessing how to reconstruct a new suite.
    """
    # Compatible objects
    if extras.safe_hasattr(suite_or_case, 'filter_by_ids'):
        return suite_or_case.filter_by_ids(test_ids)
    # TestCase objects.
    if extras.safe_hasattr(suite_or_case, 'id'):
        if suite_or_case.id() in test_ids:
            return suite_or_case
        else:
            return unittest.TestSuite()
    # Standard TestSuites or derived classes [assumed to be mutable].
    if isinstance(suite_or_case, unittest.TestSuite):
        filtered = []
        for item in suite_or_case:
            filtered.append(filter_by_ids(item, test_ids))
        suite_or_case._tests[:] = filtered
    # Everything else:
    return suite_or_case


def iterate_tests(test_suite_or_case):
    """Iterate through all of the test cases in 'test_suite_or_case'."""
    try:
        suite = iter(test_suite_or_case)
    except TypeError:
        yield test_suite_or_case
    else:
        for test in suite:
            for subtest in iterate_tests(test):
                yield subtest


def list_test(test):
    """Return the test ids that would be run if test() was run.

    When things fail to import they can be represented as well, though
    we use an ugly hack (see http://bugs.python.org/issue19746 for details)
    to determine that. The difference matters because if a user is
    filtering tests to run on the returned ids, a failed import can reduce
    the visible tests but it can be impossible to tell that the selected
    test would have been one of the imported ones.

    :return: A tuple of test ids that would run and error strings
        describing things that failed to import.
    """
    unittest_import_strs = set([
        'unittest2.loader.ModuleImportFailure.',
        'unittest.loader.ModuleImportFailure.',
        'discover.ModuleImportFailure.'
        ])
    test_ids = []
    errors = []
    for test in iterate_tests(test):
        # Much ugly.
        for prefix in unittest_import_strs:
            if test.id().startswith(prefix):
                errors.append(test.id()[len(prefix):])
                break
        else:
            test_ids.append(test.id())
    return test_ids, errors


class TestProgram(unittest.TestProgram):

    # defaults for testing
    module = None
    verbosity = 1
    failfast = catchbreak = buffer = progName = None
    _discovery_parser = None

    def __init__(self, module='__main__', defaultTest=None, argv=None,
                 testRunner=None, testLoader=unittest.defaultTestLoader,
                 exit=False, verbosity=1, failfast=None, catchbreak=None,
                 buffer=None, warnings=None, tb_locals=False):
        if isinstance(module, str):
            self.module = __import__(module)
            for part in module.split('.')[1:]:
                self.module = getattr(self.module, part)
        else:
            self.module = module
        if argv is None:
            argv = sys.argv

        self.exit = exit
        self.failfast = failfast
        self.catchbreak = catchbreak
        self.verbosity = verbosity
        self.buffer = buffer
        self.tb_locals = tb_locals
        if warnings is None and not sys.warnoptions:
            # even if DeprecationWarnings are ignored by default
            # print them anyway unless other warnings settings are
            # specified by the warnings arg or the -W python flag
            self.warnings = 'default'
        else:
            # here self.warnings is set either to the value passed
            # to the warnings args or to None.
            # If the user didn't pass a value self.warnings will
            # be None. This means that the behavior is unchanged
            # and depends on the values passed to -W.
            self.warnings = warnings
        self.defaultTest = defaultTest
        # XXX: Local edit (see http://bugs.python.org/issue22860)
        self.listtests = False
        self.load_list = None
        self.testRunner = testRunner
        self.testLoader = testLoader
        self.progName = os.path.basename(argv[0])
        self.parseArgs(argv)
        # XXX: Local edit (see http://bugs.python.org/issue22860)
        if self.load_list:
            # TODO(mtreinish): preserve existing suites (like testresources
            # does in OptimisingTestSuite.add, but with a standard protocol).
            # This is needed because the load_tests hook allows arbitrary
            # suites, even if that is rarely used.
            source = open(self.load_list, 'rb')
            try:
                lines = source.readlines()
            finally:
                source.close()
            test_ids = set(line.strip().decode('utf-8') for line in lines)
            self.test = filter_by_ids(self.test, test_ids)
        # XXX: Local edit (see http://bugs.python.org/issue22860)
        if not self.listtests:
            self.runTests()
        else:
            runner = self._get_runner()
            if extras.safe_hasattr(runner, 'list'):
                try:
                    runner.list(self.test, loader=self.testLoader)
                except TypeError:
                    runner.list(self.test)
            else:
                for test in iterate_tests(self.test):
                    sys.stdout.write('%s\n' % test.id())

    def _getParentArgParser(self):
        parser = super(TestProgram, self)._getParentArgParser()
        # XXX: Local edit (see http://bugs.python.org/issue22860)
        parser.add_argument(
            '-l', '--list', dest='listtests', default=False,
            action='store_true', help='List tests rather than executing them')
        parser.add_argument(
            '--load-list', dest='load_list', default=None,
            help='Specifies a file containing test ids, only tests matching '
                 'those ids are executed')
        return parser

    def usageExit(self, msg=None):
        if msg is None:
            msg = "Internal stestr test runner"
        super(TestProgram, self).usageExit(msg)

    def _get_runner(self):
        testRunner = self.testRunner
        if isinstance(self.testRunner, type):
            try:
                try:
                    testRunner = self.testRunner(failfast=self.failfast,
                                                 tb_locals=self.tb_locals)
                except TypeError:
                    testRunner = self.testRunner(failfast=self.failfast)
            except TypeError:
                testRunner = self.testRunner()
        # If for some reason we failed to initialize the runner initialize
        # with defaults
        if isinstance(testRunner, functools.partial):
            testRunner = self.testRunner()
        return testRunner

    def runTests(self):
        if self.catchbreak:
            unittest.installHandler()
        testRunner = self._get_runner()
        self.result = testRunner.run(self.test)
