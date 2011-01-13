# -*- encoding: utf-8 -*-
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

"""Tests for UI decorator."""

from testrepository import commands
from testrepository.ui import decorator, model
from testrepository.tests import ResourcedTestCase


class TestDecoratorUI(ResourcedTestCase):

    def test_options_overridable(self):
        base = model.UI(options=[('partial', True), ('other', False)])
        cmd = commands.Command(base)
        base.set_command(cmd)
        ui = decorator.UI(options={'partial':False}, decorated=base)
        internal_cmd = commands.Command(ui)
        ui.set_command(internal_cmd)
        self.assertEqual(False, ui.options.partial)
        self.assertEqual(False, ui.options.other)
