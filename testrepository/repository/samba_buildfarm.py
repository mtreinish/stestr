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

"""Access to the Samba build farm."""
import subunit
import urllib

from testrepository.repository import (
    AbstractRepository,
    AbstractRepositoryFactory,
    AbstractTestRun,
    RepositoryNotFound,
    )

BUILD_FARM_URL = "http://build.samba.org/"


class RepositoryFactory(AbstractRepositoryFactory):

    def initialise(klass, url):
        """Create a repository at url/path."""
        raise NotImplementedError(klass.initialise)

    def open(self, url):
        if not url.startswith(BUILD_FARM_URL):
            raise RepositoryNotFound(url)
        return Repository(url)


class Repository(AbstractRepository):
    """Access to the subunit results on the Samba build farm.
    """

    def __init__(self, base):
        """Create a repository object for the Samba build farm at base.
        """
        self.base = base.rstrip("/")+"/"
        recent_ids_url = urllib.basejoin(self.base, "+recent-ids")
        f = urllib.urlopen(recent_ids_url, "r")
        try:
            self.recent_ids = [x.rstrip("\n") for x in f.readlines()]
        finally:
            f.close()

    def count(self):
        return len(self.recent_ids)

    def latest_id(self):
        if len(self.recent_ids) == 0:
            raise KeyError("No tests in repository")
        return len(self.recent_ids) - 1

    def get_failing(self):
        raise NotImplementedError(self.get_failing)

    def get_test_run(self, run_id):
        return _HttpRun(self.base, self.recent_ids[run_id])

    def _get_inserter(self, partial):
        raise NotImplementedError(self._get_inserter)


class _HttpRun(AbstractTestRun):
    """A test run that was inserted into the repository."""

    def __init__(self, base_url, run_id):
        """Create a _HttpRun with the content subunit_content."""
        self.base_url = base_url
        self.run_id = run_id
        self.url = urllib.basejoin(self.base_url,
            "../../build/%s/+subunit" % self.run_id)

    def get_subunit_stream(self):
        return urllib.urlopen(self.url)

    def get_test(self):
        return subunit.ProtocolTestCase(self.get_subunit_stream())
