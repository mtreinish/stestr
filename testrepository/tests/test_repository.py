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

"""Tests for Repository support logic and the Repository contract."""

import datetime
import doctest

from subunit import iso8601

from testresources import TestResource
from testtools import (
    clone_test_with_new_id,
    TestResult,
    )
from testtools.matchers import DocTestMatches, raises

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


class Case(ResourcedTestCase):
    """Reference tests."""

    def passing(self):
        pass

    def failing(self):
        self.fail("oops")


def make_test(id, should_pass):
    """Make a test."""
    if should_pass:
        case = Case("passing")
    else:
        case = Case("failing")
    return clone_test_with_new_id(case, id)


def run_timed(id, duration, result):
    """Make and run a test taking duration seconds."""
    start = datetime.datetime.now(tz=iso8601.Utc())
    result.time(start)
    test = make_test(id, True)
    result.startTest(test)
    result.time(start + datetime.timedelta(seconds=duration))
    result.addSuccess(test)
    result.stopTest(test)


class TestRepositoryErrors(ResourcedTestCase):

    def test_not_found(self):
        url = 'doesntexistatall'
        error = repository.RepositoryNotFound(url)
        self.assertEqual(
            'No repository found in %s. Create one by running "testr init".'
            % url, str(error))


class TestRepositoryContract(ResourcedTestCase):

    scenarios = repo_implementations

    def get_failing(self, repo):
        """Analyze a failing stream from repo and return it."""
        run = repo.get_failing()
        analyzer = TestResult()
        run.get_test().run(analyzer)
        return analyzer

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
        self.repo_impl.initialise(self.sample_url)
        self.repo_impl.open(self.sample_url)

    def test_open_non_existent(self):
        url = 'doesntexistatall'
        self.assertThat(lambda: self.repo_impl.open(url),
            raises(repository.RepositoryNotFound(url)))

    def test_inserting_creates_id(self):
        # When inserting a stream, an id is returned from stopTestRun.
        repo = self.repo_impl.initialise(self.sample_url)
        result = repo.get_inserter()
        result.startTestRun()
        self.assertNotEqual(None, result.stopTestRun())

    def test_count(self):
        repo = self.repo_impl.initialise(self.sample_url)
        self.assertEqual(0, repo.count())
        result = repo.get_inserter()
        result.startTestRun()
        result.stopTestRun()
        self.assertEqual(1, repo.count())
        result = repo.get_inserter()
        result.startTestRun()
        result.stopTestRun()
        self.assertEqual(2, repo.count())

    def test_latest_id_empty(self):
        repo = self.repo_impl.initialise(self.sample_url)
        self.assertThat(repo.latest_id,
            raises(KeyError("No tests in repository")))

    def test_latest_id_nonempty(self):
        repo = self.repo_impl.initialise(self.sample_url)
        result = repo.get_inserter()
        result.startTestRun()
        inserted = result.stopTestRun()
        self.assertEqual(inserted, repo.latest_id())

    def test_get_failing_empty(self):
        # repositories can return a TestRun with just latest failures in it.
        repo = self.repo_impl.initialise(self.sample_url)
        analyzed = self.get_failing(repo)
        self.assertEqual(0, analyzed.testsRun)

    def test_get_failing_one_run(self):
        # repositories can return a TestRun with just latest failures in it.
        repo = self.repo_impl.initialise(self.sample_url)
        result = repo.get_inserter()
        result.startTestRun()
        make_test('passing', True).run(result)
        make_test('failing', False).run(result)
        result.stopTestRun()
        analyzed = self.get_failing(repo)
        self.assertEqual(1, analyzed.testsRun)
        self.assertEqual(1, len(analyzed.failures))
        self.assertEqual('failing', analyzed.failures[0][0].id())

    def test_get_failing_complete_runs_delete_missing_failures(self):
        # failures from complete runs replace all failures.
        repo = self.repo_impl.initialise(self.sample_url)
        result = repo.get_inserter()
        result.startTestRun()
        make_test('passing', True).run(result)
        make_test('failing', False).run(result)
        make_test('missing', False).run(result)
        result.stopTestRun()
        result = repo.get_inserter()
        result.startTestRun()
        make_test('passing', False).run(result)
        make_test('failing', True).run(result)
        result.stopTestRun()
        analyzed = self.get_failing(repo)
        self.assertEqual(1, analyzed.testsRun)
        self.assertEqual(1, len(analyzed.failures))
        self.assertEqual('passing', analyzed.failures[0][0].id())

    def test_get_failing_partial_runs_preserve_missing_failures(self):
        # failures from two runs add to existing failures, and successes remove
        # from them.
        repo = self.repo_impl.initialise(self.sample_url)
        result = repo.get_inserter()
        result.startTestRun()
        make_test('passing', True).run(result)
        make_test('failing', False).run(result)
        make_test('missing', False).run(result)
        result.stopTestRun()
        result = repo.get_inserter(partial=True)
        result.startTestRun()
        make_test('passing', False).run(result)
        make_test('failing', True).run(result)
        result.stopTestRun()
        analyzed = self.get_failing(repo)
        self.assertEqual(2, analyzed.testsRun)
        self.assertEqual(2, len(analyzed.failures))
        self.assertEqual(set(['passing', 'missing']),
            set([test[0].id() for test in analyzed.failures]))

    def test_get_test_run(self):
        repo = self.repo_impl.initialise(self.sample_url)
        result = repo.get_inserter()
        result.startTestRun()
        inserted = result.stopTestRun()
        run = repo.get_test_run(inserted)
        self.assertNotEqual(None, run)

    def test_get_subunit_from_test_run(self):
        repo = self.repo_impl.initialise(self.sample_url)
        result = repo.get_inserter()
        result.startTestRun()
        make_test('testrepository.tests.test_repository.Case.method', True).run(result)
        inserted = result.stopTestRun()
        run = repo.get_test_run(inserted)
        as_subunit = run.get_subunit_stream()
        self.assertThat(as_subunit.read(), DocTestMatches("""...test: testrepository.tests.test_repository.Case.method...
successful: testrepository.tests.test_repository.Case.method...
""", doctest.ELLIPSIS))

    def test_get_test_from_test_run(self):
        repo = self.repo_impl.initialise(self.sample_url)
        result = repo.get_inserter()
        result.startTestRun()
        make_test('testrepository.tests.test_repository.Case.method', True).run(result)
        inserted = result.stopTestRun()
        run = repo.get_test_run(inserted)
        test = run.get_test()
        result = TestResult()
        result.startTestRun()
        try:
            test.run(result)
        finally:
            result.stopTestRun()
        self.assertEqual(1, result.testsRun)

    def test_get_times_unknown_tests_are_unknown(self):
        repo = self.repo_impl.initialise(self.sample_url)
        test_ids = set(['foo', 'bar'])
        self.assertEqual(test_ids, repo.get_test_times(test_ids)['unknown'])

    def test_inserted_test_times_known(self):
        repo = self.repo_impl.initialise(self.sample_url)
        result = repo.get_inserter()
        result.startTestRun()
        test_name = 'testrepository.tests.test_repository.Case.method'
        run_timed(test_name, 1, result)
        result.stopTestRun()
        self.assertEqual({test_name: 1.0},
            repo.get_test_times([test_name])['known'])
