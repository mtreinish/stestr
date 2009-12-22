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

"""Tests for the commands module."""

from cStringIO import StringIO
import doctest
import os.path
import sys

from testresources import TestResource
from testtools.matchers import (
    DocTestMatches,
    )

from testrepository import commands
from testrepository.tests import ResourcedTestCase
from testrepository.tests.monkeypatch import monkeypatch
from testrepository.tests.stubpackage import (
    StubPackageResource,
    )


class TemporaryCommand(object):
    """A temporary command."""


class TemporaryCommandResource(TestResource):

    def __init__(self, cmd_name):
        TestResource.__init__(self)
        self.resources.append(('pkg',
            StubPackageResource('commands',
            [('%s.py' % cmd_name,
             """from testrepository.commands import Command
class %s(Command):
    def run(self):
        pass
""" % cmd_name)], init=False)))
        self.cmd_name = cmd_name

    def make(self, dependency_resources):
        pkg = dependency_resources['pkg']
        result = TemporaryCommand()
        result.path = os.path.join(pkg.base, 'commands')
        commands.__path__.append(result.path)
        return result

    def clean(self, resource):
        commands.__path__.remove(resource.path)
        name = 'testrepository.commands.%s' % self.cmd_name
        if name in sys.modules:
            del sys.modules[name]


class TestFindCommand(ResourcedTestCase):

    resources = [('cmd', TemporaryCommandResource('foo'))]

    def test_looksupcommand(self):
        cmd = commands._find_command('foo')
        self.assertIsInstance(cmd(None), commands.Command)

    def test_missing_command(self):
        self.assertRaises(KeyError, commands._find_command, 'bar')


class TestRunArgv(ResourcedTestCase):

    def stub__find_command(self, cmd_run):
        self.calls = []
        self.addCleanup(monkeypatch('testrepository.commands._find_command',
            self._find_command))
        self.cmd_run = cmd_run

    def _find_command(self, cmd_name):
        self.calls.append(cmd_name)
        real_run = self.cmd_run
        class SampleCommand(commands.Command):
            """A command that is used for testing."""
            def run(self):
                return real_run()
        return SampleCommand

    def test_looks_up_cmd(self):
        self.stub__find_command(lambda x:0)
        commands.run_argv(['testr', 'foo'], 'in', 'out', 'err')
        self.assertEqual(['foo'], self.calls)

    def test_looks_up_cmd_skips_options(self):
        self.stub__find_command(lambda x:0)
        commands.run_argv(['testr', '--version', 'foo'], 'in', 'out', 'err')
        self.assertEqual(['foo'], self.calls)

    def test_no_cmd_issues_help(self):
        self.stub__find_command(lambda x:0)
        out = StringIO()
        commands.run_argv(['testr', '--version'], 'in', out, 'err')
        self.assertEqual([], self.calls)
        self.assertThat(out.getvalue(), DocTestMatches("""testr -- a free test repository
https://launchpad.net/testrepository/

testr commands -- list commands
testr quickstart -- starter documentation
testr help [command] -- help system
""", doctest.ELLIPSIS))
