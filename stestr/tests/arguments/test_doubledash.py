#
# Copyright (c) 2012 Testrepository Contributors
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

"""Tests for the doubledash argument type."""

from testrepository.arguments import doubledash
from testrepository.tests import ResourcedTestCase


class TestArgument(ResourcedTestCase):

    def test_parses_as_string(self):
        arg = doubledash.DoubledashArgument()
        result = arg.parse(['--'])
        self.assertEqual(['--'], result)

    def test_fixed_name(self):
        arg = doubledash.DoubledashArgument()
        self.assertEqual('doubledash', arg.name)

    def test_fixed_min_max(self):
        arg = doubledash.DoubledashArgument()
        self.assertEqual(0, arg.minimum_count)
        self.assertEqual(1, arg.maximum_count)

    def test_parses_non_dash_dash_as_nothing(self):
        arg = doubledash.DoubledashArgument()
        args = ['foo', '--']
        result = arg.parse(args)
        self.assertEqual([], result)
        self.assertEqual(['foo', '--'], args)

