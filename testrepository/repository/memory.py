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

from testrepository.repository import (
    AbstractRepository,
    AbstractRepositoryFactory,
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

    def count(self):
        return len(self._runs)

    def latest_id(self):
        return self.count() - 1

    def _get_inserter(self):
        return _Inserter(self)


class _Inserter(object):
    """Insert test results into a memory repository."""

    def __init__(self, repository):
        self._repository = repository
        self._outcomes = []

    def startTestRun(self):
        pass

    def stopTestRun(self):
        self._repository._runs.append(self)
        return len(self._repository._runs) - 1

    def startTest(self, test):
        pass

    def stopTest(self, test):
        pass

    def _addOutcome(self, outcome, test, details):
        self._outcomes.append((outcome, test, details))

    def addSuccess(self, test, details=None):
        self._addOutcome('success', test, details)

    def addFailure(self, test, err=None, details=None):
        # Don't support old interface for now.
        assert err is None
        self._addOutcome('failure', test, details)

    def addError(self, test, err=None, details=None):
        assert err is None
        self._addOutcome('error', test, details)

    def addExpectedFailure(self, test, err=None, details=None):
        assert err is None
        self._addOutcome('expectedFailure', test, details)

    def addUnexpectedSuccess(self, details=None):
        self._addOutcome('unexpectedSccess', test, details)

    def addSkip(self, test, reason=None, details=None):
        assert reason is None
        self._addOutcome('skip', test, details)

