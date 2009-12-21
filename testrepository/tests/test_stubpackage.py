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

"""Tests for the stubpackage test helper."""

import os.path

from testrepository.tests import ResourcedTestCase
from testrepository.tests.stubpackage import (
    StubPackageResource,
    TempDirResource,
    )


class TestStubPackageResource(ResourcedTestCase):

    def test_has_tempdir(self):
        resource = StubPackageResource('foo', [])
        self.assertEqual(1, len(resource.resources))
        self.assertIsInstance(resource.resources[0][1], TempDirResource)

    def test_writes_package(self):
        resource = StubPackageResource('foo', [('bar.py', 'woo')])
        pkg = resource.getResource()
        self.addCleanup(resource.finishedWith, pkg)
        self.assertEqual('', file(os.path.join(pkg.base, 'foo',
            '__init__.py')).read())
        self.assertEqual('woo', file(os.path.join(pkg.base, 'foo',
            'bar.py')).read())

    def test_no__init__(self):
        resource = StubPackageResource('foo', [('bar.py', 'woo')], init=False)
        pkg = resource.getResource()
        self.addCleanup(resource.finishedWith, pkg)
        self.assertFalse(os.path.exists(os.path.join(pkg.base, 'foo',
            '__init__.py')))


class TestTempDirResource(ResourcedTestCase):
    """Tests for the StubPackage resource."""

    def test_makes_a_dir(self):
        resource = TempDirResource()
        tempdir = resource.getResource()
        try:
            self.assertTrue(os.path.exists(tempdir))
        finally:
            resource.finishedWith(tempdir)
        self.assertFalse(os.path.exists(tempdir))
