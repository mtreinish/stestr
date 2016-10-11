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

"""Tests for matchers used by or for testing testrepository."""

import sys
from testtools import TestCase


class TestWildcard(TestCase):

    def test_wildcard_equals_everything(self):
        from testrepository.tests import Wildcard
        self.assertTrue(Wildcard == 5)
        self.assertTrue(Wildcard == 'orange')
        self.assertTrue('orange' == Wildcard)
        self.assertTrue(5 == Wildcard)

    def test_wildcard_not_equals_nothing(self):
        from testrepository.tests import Wildcard
        self.assertFalse(Wildcard != 5)
        self.assertFalse(Wildcard != 'orange')

