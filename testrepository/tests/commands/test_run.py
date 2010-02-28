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

"""Tests for the run command."""

import os.path

from testrepository.commands import run
from testrepository.ui.model import UI
from testrepository.repository import memory
from testrepository.tests import ResourcedTestCase
from testrepository.tests.matchers import MatchesException
from testrepository.tests.stubpackage import TempDirResource
from testrepository.tests.test_repository import make_test


class TestCommand(ResourcedTestCase):

    resources = [('tempdir', TempDirResource())]

    def get_test_ui_and_cmd(self, options=(), args=()):
        self.dirty()
        ui = UI(options=options, args=args)
        ui.here = self.tempdir
        cmd = run.run(ui)
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

    def test_no_config_file_errors(self):
        ui, cmd = self.get_test_ui_and_cmd()
        self.assertEqual(3, cmd.execute())
        self.assertEqual(1, len(ui.outputs))
        self.assertEqual('error', ui.outputs[0][0])
        self.assertThat(ui.outputs[0][1],
            MatchesException(ValueError('No .testr.conf config file')))

    def test_no_config_settings_errors(self):
        ui, cmd = self.get_test_ui_and_cmd()
        self.set_config('')
        self.assertEqual(3, cmd.execute())
        self.assertEqual(1, len(ui.outputs))
        self.assertEqual('error', ui.outputs[0][0])
        self.assertThat(ui.outputs[0][1], MatchesException(ValueError(
            'No test_command option present in .testr.conf')))

    def test_IDFILE_failures(self):
        ui, cmd = self.get_test_ui_and_cmd(options=[('failing', True)])
        cmd.repository_factory = memory.RepositoryFactory()
        repo = cmd.repository_factory.initialise(ui.here)
        inserter = repo.get_inserter()
        inserter.startTestRun()
        make_test('passing', True).run(inserter)
        make_test('failing', False).run(inserter)
        inserter.stopTestRun()
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDOPTION\ntest_id_option=--load-list $IDFILE\n')
        self.assertEqual(0, cmd.execute())
        listfile = os.path.join(ui.here, 'failing.list')
        expected_cmd = 'foo --load-list %s| testr load' % listfile
        self.assertEqual([
            ('values', [('running', expected_cmd)]),
            ('popen', (expected_cmd,), {'shell': True}),
            ('communicate',),
            ], ui.outputs)
        # TODO: check the list file is written, and deleted.

    def test_IDFILE_not_passed_normally(self):
        ui, cmd = self.get_test_ui_and_cmd()
        cmd.repository_factory = memory.RepositoryFactory()
        repo = cmd.repository_factory.initialise(ui.here)
        inserter = repo.get_inserter()
        inserter.startTestRun()
        make_test('passing', True).run(inserter)
        make_test('failing', False).run(inserter)
        inserter.stopTestRun()
        self.set_config(
            '[DEFAULT]\ntest_command=foo $IDOPTION\ntest_id_option=--load-list $IDFILE\n')
        self.assertEqual(0, cmd.execute())
        expected_cmd = 'foo | testr load'
        self.assertEqual([
            ('values', [('running', expected_cmd)]),
            ('popen', (expected_cmd,), {'shell': True}),
            ('communicate',),
            ], ui.outputs)
