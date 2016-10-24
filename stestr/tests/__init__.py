#
# Copyright (c) 2009, 2010 Testrepository Contributors
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

"""The stestr tests and test only code."""

import unittest

import testresources
from testscenarios import generate_scenarios
from testtools import TestCase


class ResourcedTestCase(TestCase, testresources.ResourcedTestCase):
    """Make all stestr tests have resource support."""


class _Wildcard(object):
    """Object that is equal to everything."""

    def __repr__(self):
        return '*'

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


Wildcard = _Wildcard()


class StubTestCommand:

    def __init__(self, filter_tags=None):
        self.results = []
        self.filter_tags = filter_tags or set()

    def __call__(self, ui, repo):
        return self

    def get_filter_tags(self):
        return self.filter_tags


def test_suite():
    packages = [
        'arguments',
        'commands',
        'repository',
        'ui',
        ]
    names = [
        'arguments',
        'commands',
        'matchers',
        'monkeypatch',
        'repository',
        'results',
        'setup',
        'stubpackage',
        'testcommand',
        'testr',
        'ui',
        ]
    module_names = ['stestr.tests.test_' + name for name in names]
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromNames(module_names)
    result = testresources.OptimisingTestSuite()
    result.addTests(generate_scenarios(suite))
    for pkgname in packages:
        pkg = __import__('stestr.tests.' + pkgname, globals(),
            locals(), ['test_suite'])
        result.addTests(generate_scenarios(pkg.test_suite()))
    return result
