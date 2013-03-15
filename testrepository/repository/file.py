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

"""Persistent storage of test results."""

from io import BytesIO
try:
    import anydbm as dbm
except ImportError:
    import dbm
import errno
import os.path
import sys
import tempfile

import subunit
from subunit import TestProtocolClient
import testtools
from testtools.compat import _b

from testrepository.repository import (
    AbstractRepository,
    AbstractRepositoryFactory,
    AbstractTestRun,
    RepositoryNotFound,
    )
from testrepository.utils import timedelta_to_seconds


def atomicish_rename(source, target):
    if os.name != "posix" and os.path.exists(target):
        os.remove(target)
    os.rename(source, target)


class RepositoryFactory(AbstractRepositoryFactory):

    def initialise(klass, url):
        """Create a repository at url/path."""
        base = os.path.join(os.path.expanduser(url), '.testrepository')
        os.mkdir(base)
        stream = open(os.path.join(base, 'format'), 'wt')
        try:
            stream.write('1\n')
        finally:
            stream.close()
        result = Repository(base)
        result._write_next_stream(0)
        return result

    def open(self, url):
        path = os.path.expanduser(url)
        base = os.path.join(path, '.testrepository')
        try:
            stream = open(os.path.join(base, 'format'), 'rt')
        except (IOError, OSError) as e:
            if e.errno == errno.ENOENT:
                raise RepositoryNotFound(url)
            raise
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

    def _next_stream(self):
        next_content = open(os.path.join(self.base, 'next-stream'), 'rt').read()
        try:
            return int(next_content)
        except ValueError:
            raise ValueError("Corrupt next-stream file: %r" % next_content)

    def count(self):
        return self._next_stream()

    def latest_id(self):
        result = self._next_stream() - 1
        if result < 0:
            raise KeyError("No tests in repository")
        return result
 
    def get_failing(self):
        try:
            run_subunit_content = open(
                os.path.join(self.base, "failing"), 'rb').read()
        except IOError:
            err = sys.exc_info()[1]
            if err.errno == errno.ENOENT:
                run_subunit_content = _b('')
            else:
                raise
        return _DiskRun(None, run_subunit_content)

    def get_test_run(self, run_id):
        try:
            run_subunit_content = open(
                os.path.join(self.base, str(run_id)), 'rb').read()
        except IOError as e:
            if e.errno == errno.ENOENT:
                raise KeyError("No such run.")
        return _DiskRun(run_id, run_subunit_content)

    def _get_inserter(self, partial):
        return _Inserter(self, partial)

    def _get_test_times(self, test_ids):
        # May be too slow, but build and iterate.
        # 'c' because an existing repo may be missing a file.
        db = dbm.open(self._path('times.dbm'), 'c')
        try:
            result = {}
            for test_id in test_ids:
                if type(test_id) != str:
                    test_id = test_id.encode('utf8')
                # gdbm does not support get().
                try:
                    duration = db[test_id]
                except KeyError:
                    duration = None
                if duration is not None:
                    result[test_id] = float(duration)
            return result
        finally:
            db.close()

    def _path(self, suffix):
        return os.path.join(self.base, suffix)

    def _write_next_stream(self, value):
        # Note that this is unlocked and not threadsafe : for now, shrug - single
        # user, repo-per-working-tree model makes this acceptable in the short
        # term. Likewise we don't fsync - this data isn't valuable enough to
        # force disk IO.
        prefix = self._path('next-stream')
        stream = open(prefix + '.new', 'wt')
        try:
            stream.write('%d\n' % value)
        finally:
            stream.close()
        atomicish_rename(prefix + '.new', prefix)


class _DiskRun(AbstractTestRun):
    """A test run that was inserted into the repository."""

    def __init__(self, run_id, subunit_content):
        """Create a _DiskRun with the content subunit_content."""
        self._run_id = run_id
        self._content = subunit_content
        assert type(subunit_content) is bytes

    def get_id(self):
        return self._run_id

    def get_subunit_stream(self):
        return BytesIO(self._content)

    def get_test(self):
        return subunit.ProtocolTestCase(self.get_subunit_stream())


class _SafeInserter(object):

    def __init__(self, repository, partial=False):
        # XXX: Perhaps should factor into a decorator and use an unaltered
        # TestProtocolClient.
        self._repository = repository
        fd, name = tempfile.mkstemp(dir=self._repository.base)
        self.fname = name
        stream = os.fdopen(fd, 'wb')
        self.partial = partial
        # The time take by each test, flushed at the end.
        self._times = {}
        self._test_start = None
        self._time = None
        subunit_client = testtools.StreamToExtendedDecorator(
            TestProtocolClient(stream))
        self.hook = testtools.CopyStreamResult([
            subunit_client,
            testtools.StreamToDict(self._handle_test)])
        self._stream = stream

    def _handle_test(self, test_dict):
        start, stop = test_dict['timestamps']
        if None in (start, stop):
            return
        self._times[test_dict['id']] = str(timedelta_to_seconds(stop - start))

    def startTestRun(self):
        self.hook.startTestRun()
        self._run_id = None

    def stopTestRun(self):
        self.hook.stopTestRun()
        self._stream.flush()
        self._stream.close()
        run_id = self._name()
        final_path = os.path.join(self._repository.base, str(run_id))
        atomicish_rename(self.fname, final_path)
        # May be too slow, but build and iterate.
        db = dbm.open(self._repository._path('times.dbm'), 'c')
        try:
            db_times = {}
            for key, value in self._times.items():
                if type(key) != str:
                    key = key.encode('utf8')
                db_times[key] = value
            if getattr(db, 'update', None):
                db.update(db_times)
            else:
                for key, value in db_times.items():
                    db[key] = value
        finally:
            db.close()
        self._run_id = run_id

    def status(self, *args, **kwargs):
        self.hook.status(*args, **kwargs)

    def _cancel(self):
        """Cancel an insertion."""
        self._stream.close()
        os.unlink(self.fname)

    def get_id(self):
        return self._run_id


class _FailingInserter(_SafeInserter):
    """Insert a stream into the 'failing' file."""

    def _name(self):
        return "failing"


class _Inserter(_SafeInserter):

    def _name(self):
        return self._repository._allocate()

    def stopTestRun(self):
        super(_Inserter, self).stopTestRun()
        # XXX: locking (other inserts may happen while we update the failing
        # file).
        # Combine failing + this run : strip passed tests, add failures.
        # use memory repo to aggregate. a bit awkward on layering ;).
        # Should just pull the failing items aside as they happen perhaps.
        # Or use a router and avoid using a memory object at all.
        from testrepository.repository import memory
        repo = memory.Repository()
        if self.partial:
            # Seed with current failing
            inserter = testtools.ExtendedToStreamDecorator(repo.get_inserter())
            inserter.startTestRun()
            failing = self._repository.get_failing()
            failing.get_test().run(inserter)
            inserter.stopTestRun()
        inserter= testtools.ExtendedToStreamDecorator(repo.get_inserter(partial=True))
        inserter.startTestRun()
        run = self._repository.get_test_run(self.get_id())
        run.get_test().run(inserter)
        inserter.stopTestRun()
        # and now write to failing
        inserter = _FailingInserter(self._repository)
        _inserter = testtools.ExtendedToStreamDecorator(inserter)
        _inserter.startTestRun()
        try:
            repo.get_failing().get_test().run(_inserter)
        except:
            inserter._cancel()
            raise
        else:
            _inserter.stopTestRun()
        return self.get_id()
