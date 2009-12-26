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

"""In memory storage of test results."""

from testrepository.repository import AbstractRepository


class Repository(AbstractRepository):
    """In memory storage of test results."""

    def __init__(self):
        # Test runs:
        self._runs = []

    @classmethod
    def initialise(klass, url):
        """Create a repository at url/path."""
        # nothing to do :)
        return Repository()

    def count(self):
        return len(self._runs)

    def get_inserter(self):
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

    def addSkip(self, reason=None, details=None):
        assert reason is None
        self._addOutcome('skip', test, details)

