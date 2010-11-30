#
# Copyright (c) 2009, 2010 Testrepository Contributors
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

import os.path
import sys

from testresources import TestResource
from testtools.matchers import MatchesException, raises

from testrepository import commands
from testrepository.repository import file
from testrepository.tests import ResourcedTestCase
from testrepository.tests.monkeypatch import monkeypatch
from testrepository.tests.stubpackage import (
    StubPackageResource,
    )
from testrepository.ui import cli, model


class TemporaryCommand(object):
    """A temporary command."""


class TemporaryCommandResource(TestResource):

    def __init__(self, cmd_name):
        TestResource.__init__(self)
        cmd_name = cmd_name.replace('-', '_')
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
        self.assertThat(lambda: commands._find_command('bar'),
            raises(KeyError))

    def test_sets_name(self):
        cmd = commands._find_command('foo')
        self.assertEqual('foo', cmd.name)


class TestNameMangling(ResourcedTestCase):

    resources = [('cmd', TemporaryCommandResource('foo-bar'))]

    def test_looksupcommand(self):
        cmd = commands._find_command('foo-bar')
        self.assertIsInstance(cmd(None), commands.Command)

    def test_sets_name(self):
        cmd = commands._find_command('foo-bar')
        # This is arbitrary in the absence of a reason to do it any particular
        # way.
        self.assertEqual('foo_bar', cmd.name)


class TestIterCommands(ResourcedTestCase):

    resources = [
        ('cmd1', TemporaryCommandResource('one')),
        ('cmd2', TemporaryCommandResource('two')),
        ]

    def test_iter_commands(self):
        cmds = list(commands.iter_commands())
        cmds = [cmd(None).name for cmd in cmds]
        # We don't care about all the built in commands
        cmds = [cmd for cmd in cmds if cmd in ('one', 'two')]
        self.assertEqual(['one', 'two'], cmds)


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
            def execute(self):
                return real_run(self)
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
        commands.run_argv(['testr', '--version'], 'in', 'out', 'err')
        self.assertEqual(['help'], self.calls)

    def capture_ui(self, cmd):
        self.ui = cmd.ui
        return 0

    def test_runs_cmd_with_CLI_UI(self):
        self.stub__find_command(self.capture_ui)
        commands.run_argv(['testr', '--version', 'foo'], 'in', 'out', 'err')
        self.assertEqual(['foo'], self.calls)
        self.assertIsInstance(self.ui, cli.UI)

    def test_returns_0_when_None_returned_from_execute(self):
        self.stub__find_command(lambda x:None)
        self.assertEqual(0, commands.run_argv(['testr', 'foo'], 'in', 'out',
            'err'))

    def test_returns_execute_result(self):
        self.stub__find_command(lambda x:1)
        self.assertEqual(1, commands.run_argv(['testr', 'foo'], 'in', 'out',
            'err'))


class InstrumentedCommand(commands.Command):
    """A command which records methods called on it.
    
    The first line is the summary.
    """

    def _init(self):
        self.calls = []

    def execute(self):
        self.calls.append('execute')
        return commands.Command.execute(self)

    def run(self):
        self.calls.append('run')


class TestAbstractCommand(ResourcedTestCase):

    def test_execute_calls_run(self):
        cmd = InstrumentedCommand(model.UI())
        self.assertEqual(0, cmd.execute())
        self.assertEqual(['execute', 'run'], cmd.calls)

    def test_execute_calls_set_command(self):
        ui = model.UI()
        cmd = InstrumentedCommand(ui)
        cmd.execute()
        self.assertEqual(cmd, ui.cmd)

    def test_execute_does_not_run_if_set_command_errors(self):
        class FailUI(object):
            def set_command(self, ui):
                return False
        cmd = InstrumentedCommand(FailUI())
        self.assertEqual(1, cmd.execute())

    def test_shows_errors_from_execute_returns_3(self):
        class FailCommand(commands.Command):
            def run(self):
                raise Exception("foo")
        ui = model.UI()
        cmd = FailCommand(ui)
        self.assertEqual(3, cmd.execute())
        self.assertEqual(1, len(ui.outputs))
        self.assertEqual('error', ui.outputs[0][0])
        self.assertThat(ui.outputs[0][1], MatchesException(Exception('foo')))

    def test_default_repository_factory(self):
        cmd = commands.Command(model.UI())
        self.assertIsInstance(cmd.repository_factory, file.RepositoryFactory)

    def test_get_summary(self):
        cmd = InstrumentedCommand
        self.assertEqual('A command which records methods called on it.',
            cmd.get_summary())
