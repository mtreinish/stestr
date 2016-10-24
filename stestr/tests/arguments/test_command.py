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

"""Tests for the command argument."""

from testtools.matchers import raises

from stestr.arguments import command
from stestr.commands import load
from stestr.tests import ResourcedTestCase


class TestArgument(ResourcedTestCase):

    def test_looks_up_command(self):
        arg = command.CommandArgument('name')
        result = arg.parse(['load'])
        self.assertEqual([load.load], result)

    def test_no_command(self):
        arg = command.CommandArgument('name')
        self.assertThat(lambda: arg.parse(['one']),
            raises(ValueError("Could not find command 'one'.")))

