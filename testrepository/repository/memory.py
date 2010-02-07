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

"""In memory storage of test results."""

from cStringIO import StringIO

import subunit

from testrepository.repository import (
    AbstractRepository,
    AbstractRepositoryFactory,
    AbstractTestRun,
    )


class RepositoryFactory(AbstractRepositoryFactory):
    """A factory that can initialise and open memory repositories.

    This is used for testing where a repository may be created and later
    opened, but tests should not see each others repositories.
    """

    def __init__(self):
        self.repos = {}

    def initialise(self, url):
        self.repos[url] = Repository()
        return self.repos[url]

    def open(self, url):
        return self.repos[url]


class Repository(AbstractRepository):
    """In memory storage of test results."""

    def __init__(self):
        # Test runs:
        self._runs = []
        self._failing = {} # id -> test

    def count(self):
        return len(self._runs)

    def get_failing(self):
        return _Failures(self)

    def get_test_run(self, run_id):
        return self._runs[run_id]

    def latest_id(self):
        result = self.count() - 1
        if result < 0:
            raise KeyError("No tests in repository")
        return result

    def _get_inserter(self):
        return _Inserter(self)


# XXX: Too much duplication between this and _Inserter
class _Failures(AbstractTestRun):
    """Report on failures from a memory repository."""

    def __init__(self, repository):
        self._repository = repository

    def get_subunit_stream(self):
        result = StringIO()
        serialiser = subunit.TestProtocolClient(result)
        self.run(serialiser)
        result.seek(0)
        return result

    def get_test(self):
        return self

    def run(self, result):
        for outcome, test, details in self._repository._failing.itervalues():
            result.startTest(test)
            getattr(result, 'add' + outcome)(test, details=details)
            result.stopTest(test)


class _Inserter(AbstractTestRun):
    """Insert test results into a memory repository, and describe them later."""

    def __init__(self, repository):
        self._repository = repository
        self._outcomes = []

    def startTestRun(self):
        pass

    def stopTestRun(self):
        self._repository._runs.append(self)
        for record in self._outcomes:
            test_id = record[1].id()
            if record[0] in ('Failure', 'Error'):
                self._repository._failing[test_id] = record
            else:
                self._repository._failing.pop(test_id, None)
        return len(self._repository._runs) - 1

    def startTest(self, test):
        pass

    def stopTest(self, test):
        pass

    def _addOutcome(self, outcome, test, details):
        self._outcomes.append((outcome, test, details))

    def addSuccess(self, test, details=None):
        self._addOutcome('Success', test, details)

    def addFailure(self, test, err=None, details=None):
        # Don't support old interface for now.
        assert err is None
        self._addOutcome('Failure', test, details)

    def addError(self, test, err=None, details=None):
        assert err is None
        self._addOutcome('Error', test, details)

    def addExpectedFailure(self, test, err=None, details=None):
        assert err is None
        self._addOutcome('ExpectedFailure', test, details)

    def addUnexpectedSuccess(self, details=None):
        self._addOutcome('UnexpectedSccess', test, details)

    def addSkip(self, test, reason=None, details=None):
        assert reason is None
        self._addOutcome('Skip', test, details)

    def get_subunit_stream(self):
        result = StringIO()
        serialiser = subunit.TestProtocolClient(result)
        self.run(serialiser)
        result.seek(0)
        return result

    def get_test(self):
        return self

    def run(self, result):
        for outcome, test, details in self._outcomes:
            result.startTest(test)
            getattr(result, 'add' + outcome)(test, details=details)
            result.stopTest(test)
