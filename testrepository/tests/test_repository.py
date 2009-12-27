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

from testresources import TestResource

from testrepository import repository
from testrepository.repository import file, memory
from testrepository.tests import ResourcedTestCase
from testrepository.tests.stubpackage import (
    TempDirResource,
    )


class RecordingRepositoryFactory(object):
    """Test helper for tests wanting to check repository factory callers."""

    def __init__(self, calls, decorated):
        self.calls = calls
        self.factory = decorated

    def initialise(self, url):
        self.calls.append(('initialise', url))
        return self.factory.initialise(url)

    def open(self, url):
        self.calls.append(('open', url))
        return self.factory.open(url)


class DirtyTempDirResource(TempDirResource):

    def __init__(self):
        TempDirResource.__init__(self)
        self._dirty = True

    def isDirty(self):
        return True

    def _setResource(self, new_resource):
        """Set the current resource to a new value."""
        self._currentResource = new_resource
        self._dirty = True


class MemoryRepositoryFactoryResource(TestResource):

    def make(self, dependency_resources):
        return memory.RepositoryFactory()


# what repository implementations do we need to test?
repo_implementations = [
    ('file', {'repo_impl': file.RepositoryFactory(),
        'resources': [('sample_url', DirtyTempDirResource())]
        }),
    ('memory', {
        'resources': [('repo_impl', MemoryRepositoryFactoryResource())],
        'sample_url': 'memory:'}),
    ]


class TestRepositoryContract(ResourcedTestCase):

    scenarios = repo_implementations

    def test_can_initialise_with_param(self):
        repo = self.repo_impl.initialise(self.sample_url)
        self.assertIsInstance(repo, repository.AbstractRepository)

    def test_can_get_inserter(self):
        repo = self.repo_impl.initialise(self.sample_url)
        result = repo.get_inserter()
        self.assertNotEqual(None, result)

    def test_insert_stream_smoke(self):
        # We can insert some data into the repository.
        repo = self.repo_impl.initialise(self.sample_url)
        class Case(ResourcedTestCase):
            def method(self):
                pass
        case = Case('method')
        result = repo.get_inserter()
        result.startTestRun()
        case.run(result)
        result.stopTestRun()
        self.assertEqual(1, repo.count())

    def test_open(self):
        repo1 = self.repo_impl.initialise(self.sample_url)
        repo2 = self.repo_impl.open(self.sample_url)
