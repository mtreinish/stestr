# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Tests for the sql repository implementation."""

import os
import os.path
import tempfile
import uuid

import fixtures
import testtools

from stestr.repository import sql
from stestr.tests import base


class SqlRepositoryFixture(fixtures.Fixture):

    def __init__(self, url=None):
        super().__init__()
        self.url = url

    def setUp(self):
        super().setUp()
        self.repo = sql.RepositoryFactory().initialise(self.url)


class TestSqlRepository(base.TestCase):

    def setUp(self):
        super().setUp()
        # NOTE(mtreinish): Windows likes to fail if the file is already open
        # when we access it later, so lets explicitly close it before we move
        # forward
        _close_me, self.tempfile = tempfile.mkstemp(suffix='.sqlite')
        os.close(_close_me)
        self.addCleanup(os.remove, self.tempfile)
        self.url = 'sqlite:///' + self.tempfile

    def test_initialise(self):
        self.useFixture(SqlRepositoryFixture(url=self.url))

    def test_get_failing(self):
        repo = self.useFixture(SqlRepositoryFixture(url=self.url)).repo
        # NOTE: "No tests in repository"
        self.assertRaises(KeyError, repo.get_failing)
        inserter = repo.get_inserter()
        inserter.startTestRun()
        inserter.stopTestRun()
        self.assertIsInstance(repo.get_failing(), sql._Subunit2SqlRun)

    def test_inserter_output_path(self):
        repo = self.useFixture(SqlRepositoryFixture(url=self.url)).repo
        inserter = repo.get_inserter()
        inserter.startTestRun()
        inserter.stopTestRun()
        run_id = inserter.get_id()
        run_uuid = uuid.UUID(run_id)

        self.assertEqual(uuid.UUID(repo.latest_id()), run_uuid)

    def test_run_get_subunit_stream(self):
        repo = self.useFixture(SqlRepositoryFixture(url=self.url)).repo
        inserter = repo.get_inserter()
        inserter.startTestRun()
        inserter.stopTestRun()
        run_id = inserter.get_id()
        run = repo.get_test_run(run_id)

        stream = run.get_subunit_stream()
        self.assertIsNotNone(stream)
        self.assertTrue(stream.readable())
        self.assertEqual([], stream.readlines())

    @testtools.skipIf(os.name == 'nt', 'tempfile fails on appveyor')
    def test_get_metadata(self):
        repo = self.useFixture(SqlRepositoryFixture(url=self.url)).repo
        result = repo.get_inserter(metadata='fun')
        result.startTestRun()
        result.stopTestRun()
        run = repo.get_test_run(result.get_id())
        self.assertEqual('fun', run.get_metadata())

    @testtools.skipIf(os.name == 'nt', 'tempfile fails on appveyor')
    def test_find_metadata(self):
        repo = self.useFixture(SqlRepositoryFixture(url=self.url)).repo
        result = repo.get_inserter(metadata='fun')
        result.startTestRun()
        result.stopTestRun()
        result_bad = repo.get_inserter(metadata='not_fun')
        result_bad.startTestRun()
        result_bad.stopTestRun()
        run_ids = repo.find_metadata('fun')
        self.assertIn(result.get_id(), run_ids)
        self.assertNotIn(result_bad.get_id(), run_ids)

    def test_get_run_ids(self):
        repo = self.useFixture(SqlRepositoryFixture(url=self.url)).repo
        result = repo.get_inserter(metadata='fun')
        result.startTestRun()
        result.stopTestRun()
        result_bad = repo.get_inserter(metadata='not_fun')
        result_bad.startTestRun()
        result_bad.stopTestRun()
        run_ids = repo.get_run_ids()
        # Run ids are uuids so just assert there are 2 since we can't expect
        # what the id will be for each run
        self.assertEqual(2, len(run_ids))

    def test_get_run_ids_empty(self):
        repo = self.useFixture(SqlRepositoryFixture(url=self.url)).repo
        run_ids = repo.get_run_ids()
        self.assertEqual([], run_ids)

    def test_get_run_ids_with_hole(self):
        repo = self.useFixture(SqlRepositoryFixture(url=self.url)).repo
        result = repo.get_inserter()
        result.startTestRun()
        result.stopTestRun()
        result = repo.get_inserter()
        result.startTestRun()
        result.stopTestRun()
        result = repo.get_inserter()
        result.startTestRun()
        result.stopTestRun()
        run_ids = repo.get_run_ids()
        repo.remove_run_id(run_ids[1])
        # Run ids are uuids so just assert there are 2 since we can't expect
        # what the id will be for each run
        self.assertEqual(2, len(repo.get_run_ids()))

    def test_remove_ids(self):
        repo = self.useFixture(SqlRepositoryFixture(url=self.url)).repo
        result = repo.get_inserter()
        result.startTestRun()
        result.stopTestRun()
        run_ids = repo.get_run_ids()
        repo.remove_run_id(run_ids[0])
        self.assertEqual([], repo.get_run_ids())

    def test_remove_ids_id_not_in_repo(self):
        repo = self.useFixture(SqlRepositoryFixture(url=self.url)).repo
        result = repo.get_inserter()
        result.startTestRun()
        result.stopTestRun()
        invalid_id = str(uuid.uuid4())
        self.assertRaises(KeyError, repo.remove_run_id, invalid_id)
