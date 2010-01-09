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

"""Tests for the arguments package."""

from testrepository import arguments
from testrepository.tests import ResourcedTestCase


class TestAbstractArgument(ResourcedTestCase):

    def test_init_base(self):
        arg = arguments.AbstractArgument('name')
        self.assertEqual('name', arg.name)
        self.assertEqual('name', arg.summary())

    def test_init_optional(self):
        arg = arguments.AbstractArgument('name', min=0)
        self.assertEqual(0, arg.minimum_count)
        self.assertEqual('name?', arg.summary())

    def test_init_repeating(self):
        arg = arguments.AbstractArgument('name', max=None)
        self.assertEqual(None, arg.maximum_count)
        self.assertEqual('name+', arg.summary())

    def test_init_optional_repeating(self):
        arg = arguments.AbstractArgument('name', min=0, max=None)
        self.assertEqual(None, arg.maximum_count)
        self.assertEqual('name*', arg.summary())

    def test_init_arbitrary(self):
        arg = arguments.AbstractArgument('name', max=2)
        self.assertEqual('name{1,2}', arg.summary())

    def test_init_arbitrary_infinite(self):
        arg = arguments.AbstractArgument('name', min=2, max=None)
        self.assertEqual('name{2,}', arg.summary())

    def test_parsing_calls__parse_one(self):
        calls = []
        class AnArgument(arguments.AbstractArgument):
            def _parse_one(self, arg):
                calls.append(arg)
                return ('1', arg)
        argument = AnArgument('foo', max=2)
        args = ['thing', 'other', 'stranger']
        # results are returned
        self.assertEqual([('1', 'thing'), ('1', 'other')],
            argument.parse(args))
        # used args are removed
        self.assertEqual(['stranger'], args)
        # parse function was used
        self.assertEqual(['thing', 'other'], calls)

    def test_parsing_unlimited(self):
        class AnArgument(arguments.AbstractArgument):
            def _parse_one(self, arg):
                return arg
        argument = AnArgument('foo', max=None)
        args = ['thing', 'other']
        # results are returned
        self.assertEqual(['thing', 'other'], argument.parse(args))
        # used args are removed
        self.assertEqual([], args)

    def test_parsing_too_few(self):
        class AnArgument(arguments.AbstractArgument):
            def _parse_one(self, arg):
                return arg
        argument = AnArgument('foo')
        self.assertRaises(ValueError, argument.parse, [])
