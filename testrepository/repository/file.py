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

"""Persistent storage of test results."""

import os.path
import tempfile

from subunit import TestProtocolClient

from testrepository.repository import (
    AbstractRepository,
    AbstractRepositoryFactory,
    )


class RepositoryFactory(AbstractRepositoryFactory):

    def initialise(klass, url):
        """Create a repository at url/path."""
        base = os.path.join(url, '.testrepository')
        os.mkdir(base)
        stream = file(os.path.join(base, 'format'), 'wb')
        try:
            stream.write('1\n')
        finally:
            stream.close()
        result = Repository(base)
        result._write_next_stream(0)
        return result

    def open(self, url):
        base = os.path.join(url, '.testrepository')
        stream = file(os.path.join(base, 'format'), 'rb')
        if '1\n' != stream.read():
            raise ValueError(url)
        return Repository(base)


class Repository(AbstractRepository):
    """Disk based storage of test results.
    
    This repository stores each stream it receives as a file in a directory.
    Indices are then built on top of this basic store.
    
    This particular disk layout is subject to change at any time, as its
    primarily a bootstrapping exercise at this point. Any changes made are
    likely to have an automatic upgrade process.
    """

    def __init__(self, base):
        """Create a file-based repository object for the repo at 'base'.

        :param base: The path to the repository.
        """
        self.base = base
    
    def _allocate(self):
        # XXX: lock the file. K?!
        value = self.count()
        self._write_next_stream(value + 1)
        return value

    def count(self):
        return int(file(os.path.join(self.base, 'next-stream'), 'rb').read())
    
    def get_inserter(self):
        return _Inserter(self)

    def _write_next_stream(self, value):
        stream = file(os.path.join(self.base, 'next-stream'), 'wb')
        try:
            stream.write('%d\n' % value)
        finally:
            stream.close()


class _Inserter(TestProtocolClient):

    def __init__(self, repository):
        self._repository = repository
        fd, name = tempfile.mkstemp(dir=self._repository.base)
        self.fname = name
        stream = os.fdopen(fd, 'wb')
        TestProtocolClient.__init__(self, stream)

    def startTestRun(self):
        pass

    def stopTestRun(self):
        # TestProtocolClient.stopTestRun(self)
        self._stream.flush()
        self._stream.close()
        os.rename(self.fname, os.path.join(self._repository.base,
            str(self._repository._allocate())))
