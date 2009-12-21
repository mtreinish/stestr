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

import os.path
import sys

from testresources import TestResource

from testrepository import commands
from testrepository.tests import ResourcedTestCase
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
