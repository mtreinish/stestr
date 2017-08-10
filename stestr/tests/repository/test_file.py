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

"""Tests for the file repository implementation."""

import os.path
import shutil
import tempfile

import fixtures
import testtools
from testtools import matchers

from stestr.repository import file
from stestr.tests import base


class FileRepositoryFixture(fixtures.Fixture):

    def __init__(self, path=None):
        super(FileRepositoryFixture, self).__init__()
        self.path = path

    def setUp(self):
        super(FileRepositoryFixture, self).setUp()
        if self.path and os.path.isdir(self.path):
            self.tempdir = self.path
        else:
            self.tempdir = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, self.tempdir)
        self.repo = file.RepositoryFactory().initialise(self.tempdir)


class HomeDirTempDir(fixtures.Fixture):
    """Creates a temporary directory in ~."""

    def setUp(self):
        super(HomeDirTempDir, self).setUp()
        home_dir = os.path.expanduser('~')
        self.temp_dir = tempfile.mkdtemp(dir=home_dir)
        self.addCleanup(shutil.rmtree, self.temp_dir)
        self.short_path = os.path.join('~', os.path.basename(self.temp_dir))


class TestFileRepository(base.TestCase):

    def setUp(self):
        super(TestFileRepository, self).setUp()
        self.tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tempdir)

    def test_initialise(self):
        self.useFixture(FileRepositoryFixture(path=self.tempdir))
        base = os.path.join(self.tempdir, '.stestr')
        self.assertTrue(os.path.isdir(base))
        self.assertTrue(os.path.isfile(os.path.join(base, 'format')))
        with open(os.path.join(base, 'format'), 'rt') as stream:
            contents = stream.read()
        self.assertEqual("1\n", contents)
        with open(os.path.join(base, 'next-stream'), 'rt') as stream:
            contents = stream.read()
        self.assertEqual("0\n", contents)

    # Skip if windows since ~ in a path doesn't work there
    @testtools.skipIf(os.name == 'nt', "Windows doesn't support '~' expand")
    def test_initialise_expands_user_directory(self):
        short_path = self.useFixture(HomeDirTempDir()).short_path
        repo = file.RepositoryFactory().initialise(short_path)
        self.assertTrue(os.path.exists(repo.base))

    def test_inserter_output_path(self):
        repo = self.useFixture(FileRepositoryFixture()).repo
        inserter = repo.get_inserter()
        inserter.startTestRun()
        inserter.stopTestRun()
        self.assertTrue(os.path.exists(os.path.join(repo.base, '0')))

    def test_inserting_creates_id(self):
        # When inserting a stream, an id is returned from stopTestRun.
        repo = self.useFixture(FileRepositoryFixture()).repo
        result = repo.get_inserter()
        result.startTestRun()
        result.stopTestRun()
        self.assertEqual(0, result.get_id())

    # Skip if windows since ~ in a path doesn't work there
    @testtools.skipIf(os.name == 'nt', "Windows doesn't support '~' expand")
    def test_open_expands_user_directory(self):
        short_path = self.useFixture(HomeDirTempDir()).short_path
        repo1 = file.RepositoryFactory().initialise(short_path)
        repo2 = file.RepositoryFactory().open(short_path)
        self.assertEqual(repo1.base, repo2.base)

    def test_next_stream_corruption_error(self):
        repo = self.useFixture(FileRepositoryFixture()).repo
        open(os.path.join(repo.base, 'next-stream'), 'wb').close()
        self.assertThat(repo.count, matchers.Raises(
            matchers.MatchesException(
                ValueError("Corrupt next-stream file: ''"))))

    # Skip if windows since chmod doesn't work there
    @testtools.skipIf(os.name == 'nt', "Windows doesn't support chmod")
    def test_get_test_run_unexpected_ioerror_errno(self):
        repo = self.useFixture(FileRepositoryFixture()).repo
        inserter = repo.get_inserter()
        inserter.startTestRun()
        inserter.stopTestRun()
        self.assertTrue(os.path.isfile(os.path.join(repo.base, '0')))
        os.chmod(os.path.join(repo.base, '0'), 0000)
        self.assertRaises(IOError, repo.get_test_run, '0')
