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

from stestr.repository import sql
from stestr.tests import base


class SqlRepositoryFixture(fixtures.Fixture):

    def __init__(self, url=None):
        super(SqlRepositoryFixture, self).__init__()
        self.url = url

    def setUp(self):
        super(SqlRepositoryFixture, self).setUp()
        self.repo = sql.RepositoryFactory().initialise(self.url)


class TestSqlRepository(base.TestCase):

    def setUp(self):
        super(TestSqlRepository, self).setUp()
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
