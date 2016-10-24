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

from io import BytesIO
import os.path
from subprocess import PIPE

from extras import try_import
import subunit
v2_avail = try_import('subunit.ByteStreamToStreamResult')
from testtools.compat import _b
from testtools.matchers import MatchesException

from stestr.commands import list_tests
from stestr.ui.model import UI
from stestr.repository import memory
from stestr.tests import ResourcedTestCase, Wildcard
from stestr.tests.stubpackage import TempDirResource
from stestr.tests.test_repository import make_test
from stestr.tests.test_testcommand import FakeTestCommand


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

    def set_config(self, text):
        with open(self.config_path(), 'wt') as stream:
            stream.write(text)

    def setup_repo(self, cmd, ui):
        repo = cmd.repository_factory.initialise(ui.here)
        inserter = repo.get_inserter()
        inserter.startTestRun()
        inserter.status(test_id='passing', test_status='success')
        inserter.status(test_id='failing', test_status='fail')
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
        if v2_avail:
            buffer = BytesIO()
            stream = subunit.StreamResultToBytes(buffer)
            stream.status(test_id='returned', test_status='exists')
            stream.status(test_id='values', test_status='exists')
            subunit_bytes = buffer.getvalue()
        else:
            subunit_bytes = _b('returned\n\nvalues\n')
        ui.proc_outputs = [subunit_bytes]
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
            ('stream', _b('returned\nvalues\n')),
            ], ui.outputs)

    def test_filters_use_filtered_list(self):
        ui, cmd = self.get_test_ui_and_cmd(
            args=('returned', '--', 'bar', 'quux'))
        cmd.repository_factory = memory.RepositoryFactory()
        if v2_avail:
            buffer = BytesIO()
            stream = subunit.StreamResultToBytes(buffer)
            stream.status(test_id='returned', test_status='exists')
            stream.status(test_id='values', test_status='exists')
            subunit_bytes = buffer.getvalue()
        else:
            subunit_bytes = _b('returned\nvalues\n')
        ui.proc_outputs = [subunit_bytes]
        self.setup_repo(cmd, ui)
        self.set_config(
            '[DEFAULT]\ntest_command=foo $LISTOPT $IDOPTION\n'
            'test_id_option=--load-list $IDFILE\n'
            'test_list_option=--list\n')
        retcode = cmd.execute()
        expected_cmd = 'foo --list  bar quux'
        self.assertEqual([
            ('values', [('running', expected_cmd)]),
            ('popen', (expected_cmd,),
             {'shell': True, 'stdout': PIPE, 'stdin': PIPE}),
            ('communicate',),
            ('stream', _b('returned\n')),
            ], ui.outputs)
        self.assertEqual(0, retcode)
