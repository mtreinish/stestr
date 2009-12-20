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

"""Tests for setup.py."""

import commands
import os.path

from testtools import (
    TestCase,
    )

class TestCanSetup(TestCase):

    def test_bdist(self):
        # Single smoke test to make sure we can build a package.
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'setup.py')
        status, output = commands.getstatusoutput(path + ' bdist')
        self.assertEqual(0, status)
