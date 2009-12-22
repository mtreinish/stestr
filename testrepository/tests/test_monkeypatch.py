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

"""Tests for the monkeypatch helper."""

from testrepository.tests import ResourcedTestCase
from testrepository.tests.monkeypatch import monkeypatch

reference = 23

class TestMonkeyPatch(ResourcedTestCase):

    def test_patch_and_restore(self):
        cleanup = monkeypatch(
            'testrepository.tests.test_monkeypatch.reference', 45)
        self.assertEqual(45, reference)
        cleanup()
        self.assertEqual(23, reference)
