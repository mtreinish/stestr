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


import io
from operator import methodcaller
import os.path
import subprocess

import sqlalchemy
from sqlalchemy import orm
import subunit.v2
from subunit2sql.db import api as db_api
from subunit2sql import read_subunit
from subunit2sql import shell
from subunit2sql import write_subunit
import testtools

from stestr.repository import abstract as repository


def atomicish_rename(source, target):
    if os.name != "posix" and os.path.exists(target):
        os.remove(target)
    os.rename(source, target)


class RepositoryFactory(repository.AbstractRepositoryFactory):

    def initialise(klass, url):
        """Create a repository at url/path."""
        print("WARNING: The SQL repository type is still experimental. You "
              "might encounter issues while using it.")
        result = Repository(url)
        # TODO(mtreinish): Figure out the python api to run the migrations for
        # setting up the schema.
        subprocess.call(['subunit2sql-db-manage', '--database-connection', url,
                         'upgrade', 'head'])
        return result

    def open(self, url):
        # TODO(mtreinish): Figure out a method to verify the DB exists and
        # raise RepositoryNotFound if it doesn't
        repo = Repository(url)
        return repo


class Repository(repository.AbstractRepository):
    """subunit2sql based storage of test results.

    This repository stores each stream in a subunit2sql DB. Refer to the
    subunit2sql documentation for
    """

    def __init__(self, url):
        """Create a subunit2sql-based repository object for the repo at 'url'.

        :param base: The path to the repository.
        """
        self.base = url
        self.engine = sqlalchemy.create_engine(url)
        self.session_factory = orm.sessionmaker(bind=self.engine,
                                                autocommit=True)

    # TODO(mtreinish): We need to add a subunit2sql api to get the count
    def count(self):
        super(Repository, self).count()

    def _get_latest_run(self):
        session = self.session_factory()
        latest_run = db_api.get_latest_run(session)
        session.close()
        if not latest_run:
            raise KeyError("No tests in repository")
        return latest_run

    def latest_id(self):
        return self._get_latest_run().uuid

    def get_failing(self):
        latest_run = self._get_latest_run()
        session = self.session_factory()
        failed_test_runs = db_api.get_test_runs_by_status_for_run_ids(
            'fail', [latest_run.id], session=session)
        session.close()
        return _Subunit2SqlRun(self.base, None, test_runs=failed_test_runs)

    def get_test_run(self, run_id):
        return _Subunit2SqlRun(self.base, run_id)

    def _get_inserter(self, partial):
        return _SqlInserter(self, partial)

    def _get_test_times(self, test_ids):
        result = {}
        # TODO(mtreinish): after subunit2sql adds a bulk query for getting
        # multiple tests by test_id at once remove the for loop
        session = self.session_factory()
        for test_id in test_ids:
            test = db_api.get_test_by_test_id(test_id, session=session)
            if test:
                result[test_id] = test.run_time
        session.close()
        return result


class _Subunit2SqlRun(repository.AbstractTestRun):
    """A test run that was inserted into the repository."""

    def __init__(self, url, run_id, test_runs=None):
        engine = sqlalchemy.create_engine(url)
        self.session_factory = orm.sessionmaker(bind=engine)
        self._run_id = run_id
        self._test_runs = test_runs

    def get_id(self):
        return self._run_id

    def get_subunit_stream(self):
        stream = io.BytesIO()
        if self._run_id:
            session = self.session_factory()
            test_runs = db_api.get_tests_run_dicts_from_run_id(self._run_id,
                                                               session)
            session.close()
        else:
            test_runs = self._test_runs
        output = subunit.v2.StreamResultToBytes(stream)
        output.startTestRun()
        for test_id in test_runs:
            test = test_runs[test_id]
            # NOTE(mtreinish): test_run_metadata is not guaranteed to be
            # present for the test run
            metadata = test.get('metadata', None)
            write_subunit.write_test(output, test['start_time'],
                                     test['stop_time'], test['status'],
                                     test_id, metadata)
        output.stopTestRun()
        stream.seek(0)
        return stream

    def get_test(self):
        case = subunit.ProtocolTestCase(self.get_subunit_stream())

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


class _SqlInserter(repository.AbstractTestRun):
    """Insert test results into a sql repository."""

    def __init__(self, repository, partial=False):
        self._repository = repository
        self.partial = partial
        self._subunit = None

    # TODO(mtreinish): Right now the entire stream is stored in memory and
    # then processed by subunit2sql.read_subunit when it is finished. It
    # would probably be better to write to the db as a _handle_test hook in
    # realtime
    def startTestRun(self):
        self._subunit = io.BytesIO()
        self.hook = subunit.v2.StreamResultToBytes(self._subunit)
        self.hook.startTestRun()
        self._run_id = None

    def stopTestRun(self):
        self.hook.stopTestRun()
        self._subunit.seek(0)
        # Create a new session factory
        engine = sqlalchemy.create_engine(self._repository.base)
        session_factory = orm.sessionmaker(bind=engine, autocommit=True)
        # TODO(mtreinish): Enable attachments
        results = read_subunit.ReadSubunit(self._subunit, attachments=False,
                                           use_wall_time=True).get_results()

        run_time = results.pop('run_time')
        totals = shell.get_run_totals(results)
        session = session_factory()
        db_run = db_api.create_run(totals['skips'], totals['fails'],
                                   totals['success'], run_time, artifacts=None,
                                   id=None, run_at=None,
                                   session=session)
        self._run_id = db_run.uuid
        for test in results:
            db_test = db_api.get_test_by_test_id(test, session)
            if not db_test:
                if results[test]['status'] == 'success':
                    success = 1
                    fails = 0
                elif results[test]['status'] == 'fail':
                    fails = 1
                    success = 0
                else:
                    fails = 0
                    success = 0
                run_time = read_subunit.get_duration(
                    results[test]['start_time'],
                    results[test]['end_time'])
                db_test = db_api.create_test(test, (success + fails), success,
                                             fails, run_time,
                                             session)
            else:
                test_values = shell.increment_counts(db_test, results[test])
                # If skipped nothing to update
                if test_values:
                    db_api.update_test(test_values, db_test.id, session)
            test_run = db_api.create_test_run(db_test.id, db_run.id,
                                              results[test]['status'],
                                              results[test]['start_time'],
                                              results[test]['end_time'],
                                              session)
            if results[test]['metadata']:
                db_api.add_test_run_metadata(
                    results[test]['metadata'], test_run.id,
                    session)
            if results[test]['attachments']:
                db_api.add_test_run_attachments(results[test]['attachments'],
                                                test_run.id, session)
        session.close()

    def status(self, *args, **kwargs):
        self.hook.status(*args, **kwargs)

    def get_id(self):
        return self._run_id
