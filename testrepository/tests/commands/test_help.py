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

"""Tests for the help command."""

from testrepository.commands import help, load
from testrepository.ui.model import UI
from testrepository.tests import ResourcedTestCase


class TestCommand(ResourcedTestCase):

    def get_test_ui_and_cmd(self):
        ui = UI(args=['load'])
        cmd = help.help(ui)
        ui.set_command(cmd)
        return ui, cmd

    def test_shows_rest_of__doc__(self):
        ui, cmd = self.get_test_ui_and_cmd()
        cmd.execute()
        self.assertEqual([('rest', load.load.__doc__)], ui.outputs)
