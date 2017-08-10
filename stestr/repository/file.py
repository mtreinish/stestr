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

"""Persistent storage of test results."""

import errno
from io import BytesIO
from operator import methodcaller
import os
import sys
import tempfile

from future.moves.dbm import dumb as my_dbm
from subunit import TestProtocolClient
import subunit.v2
import testtools
from testtools.compat import _b

from stestr.repository import abstract as repository
from stestr import utils


def atomicish_rename(source, target):
    if os.name != "posix" and os.path.exists(target):
        os.remove(target)
    os.rename(source, target)


class RepositoryFactory(repository.AbstractRepositoryFactory):

    def initialise(klass, url):
        """Create a repository at url/path."""
        base = os.path.join(os.path.expanduser(url), '.stestr')
        os.mkdir(base)
        with open(os.path.join(base, 'format'), 'wt') as stream:
            stream.write('1\n')
        result = Repository(base)
        result._write_next_stream(0)
        return result

    def open(self, url):
        path = os.path.expanduser(url)
        base = os.path.join(path, '.stestr')
        try:
            stream = open(os.path.join(base, 'format'), 'rt')
        except (IOError, OSError) as e:
            if e.errno == errno.ENOENT:
                raise repository.RepositoryNotFound(url)
            raise
        with stream:
            if '1\n' != stream.read():
                raise ValueError(url)
        return Repository(base)


class Repository(repository.AbstractRepository):
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
        with open(os.path.join(self.base, 'next-stream'), 'rt') as fp:
            next_content = fp.read()
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
            with open(os.path.join(self.base, "failing"), 'rb') as fp:
                run_subunit_content = fp.read()
        except IOError:
            err = sys.exc_info()[1]
            if err.errno == errno.ENOENT:
                run_subunit_content = _b('')
            else:
                raise
        return _DiskRun(None, run_subunit_content)

    def get_test_run(self, run_id):
        try:
            with open(os.path.join(self.base, str(run_id)), 'rb') as fp:
                run_subunit_content = fp.read()
        except IOError as e:
            if e.errno == errno.ENOENT:
                raise KeyError("No such run.")
            else:
                raise
        return _DiskRun(run_id, run_subunit_content)

    def _get_inserter(self, partial, run_id=None):
        return _Inserter(self, partial, run_id)

    def _get_test_times(self, test_ids):
        # May be too slow, but build and iterate.
        # 'c' because an existing repo may be missing a file.
        try:
            db = my_dbm.open(self._path('times.dbm'), 'c')
        except my_dbm.error:
            os.remove(self._path('times.dbm'))
            db = my_dbm.open(self._path('times.dbm'), 'c')
        try:
            result = {}
            for test_id in test_ids:
                if type(test_id) != str:
                    test_id = test_id.encode('utf8')
                stripped_test_id = utils.cleanup_test_name(test_id)
                # gdbm does not support get().
                try:
                    duration = db[stripped_test_id]
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
        # Note that this is unlocked and not threadsafe : single
        # user, repo-per-working-tree model makes this acceptable in the short
        # term. Likewise we don't fsync - this data isn't valuable enough to
        # force disk IO.
        prefix = self._path('next-stream')
        with open(prefix + '.new', 'wt') as stream:
            stream.write('%d\n' % value)
        atomicish_rename(prefix + '.new', prefix)


class _DiskRun(repository.AbstractTestRun):
    """A test run that was inserted into the repository."""

    def __init__(self, run_id, subunit_content):
        """Create a _DiskRun with the content subunit_content."""
        self._run_id = run_id
        self._content = subunit_content
        assert type(subunit_content) is bytes

    def get_id(self):
        return self._run_id

    def get_subunit_stream(self):
        # Transcode - we want V2.
        v1_stream = BytesIO(self._content)
        v1_case = subunit.ProtocolTestCase(v1_stream)
        output = BytesIO()
        output_stream = subunit.v2.StreamResultToBytes(output)
        output_stream = testtools.ExtendedToStreamDecorator(output_stream)
        output_stream.startTestRun()
        try:
            v1_case.run(output_stream)
        finally:
            output_stream.stopTestRun()
        output.seek(0)
        return output

    def get_test(self):
        # case = subunit.ProtocolTestCase(self.get_subunit_stream())
        case = subunit.ProtocolTestCase(BytesIO(self._content))

        def wrap_result(result):
            # Wrap in a router to mask out startTestRun/stopTestRun from the
            # ExtendedToStreamDecorator.
            result = testtools.StreamResultRouter(
                result, do_start_stop_run=False)
            # Wrap that in ExtendedToStreamDecorator to convert v1 calls to
            # StreamResult.
            return testtools.ExtendedToStreamDecorator(result)
        return testtools.DecorateTestCaseResult(
            case, wrap_result, methodcaller('startTestRun'),
            methodcaller('stopTestRun'))


class _SafeInserter(object):

    def __init__(self, repository, partial=False, run_id=None):
        # XXX: Perhaps should factor into a decorator and use an unaltered
        # TestProtocolClient.
        self._repository = repository
        self._run_id = run_id
        if not self._run_id:
            fd, name = tempfile.mkstemp(dir=self._repository.base)
            self.fname = name
            stream = os.fdopen(fd, 'wb')
        else:
            self.fname = os.path.join(self._repository.base, self._run_id)
            stream = open(self.fname, 'ab')
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
        if test_dict['status'] == 'exists' or None in (start, stop):
            return
        test_id = utils.cleanup_test_name(test_dict['id'])
        self._times[test_id] = str((stop - start).total_seconds())

    def startTestRun(self):
        self.hook.startTestRun()

    def stopTestRun(self):
        self.hook.stopTestRun()
        self._stream.flush()
        self._stream.close()
        run_id = self._name()
        if not self._run_id:
            final_path = os.path.join(self._repository.base, str(run_id))
            atomicish_rename(self.fname, final_path)
        # May be too slow, but build and iterate.
        db = my_dbm.open(self._repository._path('times.dbm'), 'c')
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
        if not self._run_id:
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
        if not self._run_id:
            return self._repository._allocate()
        else:
            return self._run_id

    def stopTestRun(self):
        super(_Inserter, self).stopTestRun()
        # XXX: locking (other inserts may happen while we update the failing
        # file).
        # Combine failing + this run : strip passed tests, add failures.
        # use memory repo to aggregate. a bit awkward on layering ;).
        # Should just pull the failing items aside as they happen perhaps.
        # Or use a router and avoid using a memory object at all.
        from stestr.repository import memory
        repo = memory.Repository()
        if self.partial:
            # Seed with current failing
            inserter = testtools.ExtendedToStreamDecorator(repo.get_inserter())
            inserter.startTestRun()
            failing = self._repository.get_failing()
            failing.get_test().run(inserter)
            inserter.stopTestRun()
        inserter = testtools.ExtendedToStreamDecorator(
            repo.get_inserter(partial=True))
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
        except Exception:
            inserter._cancel()
            raise
        else:
            _inserter.stopTestRun()
        return self.get_id()
