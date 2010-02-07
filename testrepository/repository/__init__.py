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

"""Storage of test results.

A Repository provides storage and indexing of results.

The AbstractRepository class defines the contract to which any Repository 
implementation must adhere.

The file submodule is the usual repository that code will use for local
access, and the memory submodule provides a memory only repository useful for
testing.

Repositories are identified by their URL, and new ones are made by calling
the initialize function in the appropriate repository module.
"""

import subunit.test_results

class AbstractRepositoryFactory(object):
    """Interface for making or opening repositories."""

    def initialise(self, url):
        """Create a repository at URL. 

        Call on the class of the repository you wish to create.
        """
        raise NotImplementedError(self.initialise)

    def open(self, url):
        """Open the repository at url."""
        raise NotImplementedError(self.open)


class AbstractRepository(object):
    """The base class for Repository implementations.

    There are no interesting attributes or methods as yet.
    """

    def count(self):
        """Return the number of test runs this repository has stored.
        
        :return count: The count of test runs stored in the repositor.
        """
        raise NotImplementedError(self.count)

    def get_failing(self):
        """Get a TestRun that contains all of and only current failing tests.

        :return: a TestRun.
        """
        raise NotImplementedError(self.get_failing)

    def get_inserter(self):
        """Get an inserter that will insert a test run into the repository.

        Repository implementations should implement _get_inserter.

        :return an inserter: Inserters meet the extended TestResult protocol
            that testtools 0.9.2 and above offer. The startTestRun and
            stopTestRun methods in particular must be called.
        """
        return subunit.test_results.AutoTimingTestResultDecorator(
            self._get_inserter())
    
    def _get_inserter(self):
        """Get an inserter for get_inserter.
        
        The result is decorated with an AutoTimingTestResultDecorator.
        """
        raise NotImplementedError(self._get_inserter)

    def get_test_run(self, run_id):
        """Retrieve a TestRun object for run_id.

        :param run_id: The test run id to retrieve.
        :return: A TestRun object.
        """
        raise NotImplementedError(self.get_test_run)

    def latest_id(self):
        """Return the run id for the most recently inserted test run."""
        raise NotImplementedError(self.latest_id)


class AbstractTestRun(object):
    """A test run that has been stored in a repository."""

    def get_subunit_stream(self):
        """Get a subunit stream for this test run."""
        raise NotImplementedError(self.get_subunit_stream)

    def get_test(self):
        """Get a testtools.TestCase-like object that can be run.

        :return: A TestCase like object which can be run to get the individual
            tests reported to a testtools.TestResult.
        """
        raise NotImplementedError(self.get_test)
