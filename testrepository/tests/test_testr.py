#
# Copyright (c) 2009 Testrepository Contributors
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

"""Tests for testr."""

import doctest
import os.path
import subprocess
import sys

from testresources import TestResource
from testtools.matchers import (
    DocTestMatches,
    )

from testrepository.tests import ResourcedTestCase
from testrepository.tests.stubpackage import StubPackageResource


class StubbedTestr(object):
    """Testr executable with replaced testrepository package for testing."""

    def __init__(self, testrpath):
        self.execpath = testrpath

    def execute(self, args):
        # sys.executable is used so that this works on windows.
        proc = subprocess.Popen([sys.executable, self.execpath] + args,
            env={'PYTHONPATH': self.stubpackage.base},
            stdout=subprocess.PIPE, stdin=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        out, err = proc.communicate()
        return proc.returncode, out


class StubbedTestrResource(TestResource):

    resources = [("stubpackage", StubPackageResource('testrepository',
        [('commands.py', r"""import sys
def run_argv(argv, stdin, stdout, stderr):
    sys.stdout.write("%s %s %s\n" % (sys.stdin is stdin, sys.stdout is stdout,
        sys.stderr is stderr))
    sys.stdout.write("%s\n" % argv)
    return len(argv) - 1
""")]))]

    def make(self, dependency_resources):
        stub = dependency_resources['stubpackage']
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'testr')
        # Make a copy of the testr script as running in place uses the current
        # library, not the stub library.
        execpath = os.path.join(stub.base, 'testr')
        source = file(path, 'rb')
        try:
            testr_contents = source.read()
        finally:
            source.close()
        target = file(execpath, 'wb')
        try:
            target.write(testr_contents)
        finally:
            target.close()
        return StubbedTestr(execpath)


class TestExecuted(ResourcedTestCase):
    """Tests that execute testr. These tests are (moderately) expensive!."""

    resources = [('testr', StubbedTestrResource())]

    def test_runs_and_returns_run_argv_some_args(self):
        status, output = self.testr.execute(["foo bar", "baz"])
        self.assertEqual(2, status)
        self.assertThat(output, DocTestMatches("""True True True
[..., 'foo bar', 'baz']\n""", doctest.ELLIPSIS))

    def test_runs_and_returns_run_argv_no_args(self):
        status, output = self.testr.execute([])
        self.assertThat(output, DocTestMatches("""True True True
[...]\n""", doctest.ELLIPSIS))
        self.assertEqual(0, status)
