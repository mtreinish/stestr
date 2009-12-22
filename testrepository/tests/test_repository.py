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

"""Tests for Repository support logic and the Repository contract."""

from testrepository.repository import file, memory
from testrepository.tests import ResourcedTestCase
from testrepository.tests.stubpackage import TempDirResource


# what repository implementations do we need to test?
def file_repo_factory(test):
    return file.initialize(test.tempdir)
def memory_repo_factory(test):
    return memory.Repository()
repo_implementations = [
    ('file', {'repo_factory': file_repo_factory,
        'resources': [('tempdir', TempDirResource())]}),
    ('memory', {'repo_factory': memory_repo_factory}),
    ]


class TestRepositoryContract(ResourcedTestCase):

    scenarios = repo_implementations

    def test_factory_returns_object(self):
        repo = self.repo_factory(self)
        self.assertNotEqual(None, repo)
