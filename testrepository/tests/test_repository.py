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

from testrepository import repository
from testrepository.repository import file, memory
from testrepository.tests import ResourcedTestCase
from testrepository.tests.stubpackage import (
    TempDirResource,
    )

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


# what repository implementations do we need to test?
repo_implementations = [
    ('file', {'repo_impl': file.Repository,
        'resources': [('sample_url', DirtyTempDirResource())]
        }),
    ('memory', {'repo_impl': memory.Repository,
        'sample_url': 'memory:'}),
    ]


class TestRepositoryContract(ResourcedTestCase):

    scenarios = repo_implementations

    def test_can_initialise_with_param(self):
        repo = self.repo_impl.initialise(self.sample_url)
        self.assertIsInstance(repo, repository.AbstractRepository)
