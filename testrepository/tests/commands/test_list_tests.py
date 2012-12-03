#
# Copyright (c) 2010 Testrepository Contributors
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

"""Tests for the list_tests command."""

import os.path
from subprocess import PIPE

from testtools.matchers import MatchesException

from testrepository.commands import list_tests
from testrepository.ui.model import UI
from testrepository.repository import memory
from testrepository.tests import ResourcedTestCase, Wildcard
from testrepository.tests.stubpackage import TempDirResource
from testrepository.tests.test_repository import make_test
from testrepository.tests.test_testcommand import FakeTestCommand


class TestCommand(ResourcedTestCase):

    resources = [('tempdir', TempDirResource())]

    def get_test_ui_and_cmd(self, options=(), args=()):
        self.dirty()
        ui = UI(options=options, args=args)
        ui.here = self.tempdir
        cmd = list_tests.list_tests(ui)
        ui.set_command(cmd)
        return ui, cmd

    def dirty(self):
        # Ugly: TODO - improve testresources to make this go away.
        dict(self.resources)['tempdir']._dirty = True

    def config_path(self):
        return os.path.join(self.tempdir, '.testr.conf')

    def set_config(self, bytes):
        stream = file(self.config_path(), 'wb')
        try:
            stream.write(bytes)
        finally:
            stream.close()

    def setup_repo(self, cmd, ui):
        repo = cmd.repository_factory.initialise(ui.here)
        inserter = repo.get_inserter()
        inserter.startTestRun()
        make_test('passing', True).run(inserter)
        make_test('failing', False).run(inserter)
        inserter.stopTestRun()

    def test_no_config_file_errors(self):
        ui, cmd = self.get_test_ui_and_cmd()
        self.assertEqual(3, cmd.execute())
        self.assertEqual(1, len(ui.outputs))
        self.assertEqual('error', ui.outputs[0][0])
        self.assertThat(ui.outputs[0][1],
            MatchesException(ValueError('No .testr.conf config file')))

    def test_calls_list_tests(self):
        ui, cmd = self.get_test_ui_and_cmd(args=('--', 'bar', 'quux'))
        cmd.repository_factory = memory.RepositoryFactory()
        ui.proc_outputs = ['returned\n\nvalues\n']
        self.setup_repo(cmd, ui)
        self.set_config(
            '[DEFAULT]\ntest_command=foo $LISTOPT $IDOPTION\n'
            'test_id_option=--load-list $IDFILE\n'
            'test_list_option=--list\n')
        self.assertEqual(0, cmd.execute())
        expected_cmd = 'foo --list  bar quux'
        self.assertEqual([
            ('values', [('running', expected_cmd)]),
            ('popen', (expected_cmd,),
             {'shell': True, 'stdout': PIPE, 'stdin': PIPE}),
            ('communicate',),
            ('stream', 'returned\nvalues\n'),
            ], ui.outputs)

    def test_filters_use_filtered_list(self):
        ui, cmd = self.get_test_ui_and_cmd(
            args=('returned', '--', 'bar', 'quux'))
        cmd.repository_factory = memory.RepositoryFactory()
        ui.proc_outputs = ['returned\n\nvalues\n']
        self.setup_repo(cmd, ui)
        self.set_config(
            '[DEFAULT]\ntest_command=foo $LISTOPT $IDOPTION\n'
            'test_id_option=--load-list $IDFILE\n'
            'test_list_option=--list\n')
        self.assertEqual(0, cmd.execute())
        expected_cmd = 'foo --list  bar quux'
        self.assertEqual([
            ('values', [('running', expected_cmd)]),
            ('popen', (expected_cmd,),
             {'shell': True, 'stdout': PIPE, 'stdin': PIPE}),
            ('communicate',),
            ('stream', 'returned\n'),
            ], ui.outputs)
