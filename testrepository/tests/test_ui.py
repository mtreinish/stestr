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

"""Tests for UI support logic and the UI contract."""

from cStringIO import StringIO

from testrepository import commands
from testrepository.ui import cli, model
from testrepository.tests import ResourcedTestCase


def cli_ui_factory(input_streams=None, options=()):
    if input_streams and len(input_streams) > 1:
        # TODO: turn additional streams into argv and simulated files, or
        # something - however, may need to be cli specific tests at that
        # point.
        raise NotImplementedError(cli_ui_factory)
    stdout = StringIO()
    if input_streams:
        stdin = StringIO(input_streams[0][1])
    else:
        stdin = StringIO()
    stderr = StringIO()
    argv = []
    for option, value in options:
        # only bool handled so far
        if value:
            argv.append('--%s' % option)
    return cli.UI(argv, stdin, stdout, stderr)


# what ui implementations do we need to test?
ui_implementations = [
    ('CLIUI', {'ui_factory': cli_ui_factory}),
    ('ModelUI', {'ui_factory': model.UI}),
    ]


class TestUIContract(ResourcedTestCase):

    scenarios = ui_implementations

    def test_factory_noargs(self):
        ui = self.ui_factory()

    def test_factory_input_stream_args(self):
        ui = self.ui_factory([('subunit', 'value')])

    def test_here(self):
        ui = self.ui_factory()
        cmd = commands.Command(ui)
        ui.set_command(cmd)
        self.assertNotEqual(None, ui.here)

    def test_iter_streams_load_stdin_use_case(self):
        # A UI can be asked for the streams that a command has indicated it
        # accepts, which is what load < foo will require.
        ui = self.ui_factory([('subunit', 'test: foo\nsuccess: foo\n')])
        cmd = commands.Command(ui)
        cmd.input_streams = ['subunit+']
        ui.set_command(cmd)
        results = []
        for result in ui.iter_streams('subunit'):
            results.append(result.read())
        self.assertEqual(['test: foo\nsuccess: foo\n'], results)

    def test_iter_streams_unexpected_type_raises(self):
        ui = self.ui_factory()
        cmd = commands.Command(ui)
        ui.set_command(cmd)
        self.assertRaises(KeyError, ui.iter_streams, 'subunit')

    def test_output_values(self):
        # output_values can be called and takes a list of things to output.
        ui = self.ui_factory()
        cmd = commands.Command(ui)
        ui.set_command(cmd)
        ui.output_values([('foo', 1), ('bar', 'quux')])

    def test_set_command(self):
        # All ui objects can be given their command.
        ui = self.ui_factory()
        cmd = commands.Command(ui)
        ui.set_command(cmd)

    def test_options_at_options(self):
        ui = self.ui_factory()
        cmd = commands.Command(ui)
        ui.set_command(cmd)
        self.assertEqual(False, ui.options.quiet)

    def test_options_when_set_at_options(self):
        ui = self.ui_factory(options=[('quiet', True)])
        cmd = commands.Command(ui)
        ui.set_command(cmd)
        self.assertEqual(True, ui.options.quiet)
