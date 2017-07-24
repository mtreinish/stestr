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


import datetime
import io
import os.path
import re
import subprocess
import sys

import six
import sqlalchemy
from sqlalchemy import orm
import subunit.v2
from subunit2sql.db import api as db_api
from subunit2sql import read_subunit
from subunit2sql import shell
from subunit2sql import write_subunit
import testtools

from stestr.repository import abstract as repository
from stestr import utils


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
        proc = subprocess.Popen(['subunit2sql-db-manage',
                                 '--database-connection', url, 'upgrade',
                                 'head'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, err = proc.communicate()
        sys.stdout.write(six.text_type(out))
        sys.stderr.write(six.text_type(err))

        return result

    def open(self, url):
        repo = Repository(url)
        # To test the repository's existence call get_ids_for_all_tests()
        # if it raises an OperationalError that means the DB doesn't exist or
        # it couldn't connect, either way the repository was not found.
        try:
            session = repo.session_factory()
            db_api.get_ids_for_all_tests(session=session)
            session.close()
        except sqlalchemy.exc.OperationalError:
            raise repository.RepositoryNotFound(url)
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
        self.session_factory = orm.sessionmaker(bind=self.engine)

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

    def _get_inserter(self, partial, run_id=None):
        return _SqlInserter(self, partial, run_id)

    def _get_test_times(self, test_ids):
        result = {}
        # TODO(mtreinish): after subunit2sql adds a bulk query for getting
        # multiple tests by test_id at once remove the for loop
        session = self.session_factory()
        for test_id in test_ids:
            stripped_test_id = utils.cleanup_test_name(test_id)
            test = db_api.get_test_by_test_id(stripped_test_id,
                                              session=session)
            if test:
                # NOTE(mtreinish): We need to make sure the test_id with attrs
                # is used in the output dict, otherwise the scheduler won't
                # see it
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
        stream = self.get_subunit_stream()
        case = subunit.ByteStreamToStreamResult(stream)
        return case


class _SqlInserter(repository.AbstractTestRun):
    """Insert test results into a sql repository."""

    def __init__(self, repository, partial=False, run_id=None):
        self._repository = repository
        self.partial = partial
        self._subunit = None
        self._run_id = run_id
        # Create a new session factory
        self.engine = sqlalchemy.create_engine(self._repository.base)
        self.session_factory = orm.sessionmaker(bind=self.engine,
                                                autocommit=True)

    def startTestRun(self):
        self._subunit = io.BytesIO()
        self.subunit_stream = subunit.v2.StreamResultToBytes(self._subunit)
        self.hook = testtools.CopyStreamResult([
            testtools.StreamToDict(self._handle_test),
            self.subunit_stream])
        self.hook.startTestRun()
        self.start_time = datetime.datetime.utcnow()
        session = self.session_factory()
        if not self._run_id:
            self.run = db_api.create_run(session=session)
            self._run_id = self.run.uuid
        else:
            int_id = db_api.get_run_id_from_uuid(self._run_id, session=session)
            self.run = db_api.get_run_by_id(int_id, session=session)
        session.close()
        self.totals = {}

    def _update_test(self, test_dict, session, start_time, stop_time):
        test_id = utils.cleanup_test_name(test_dict['id'])
        db_test = db_api.get_test_by_test_id(test_id, session)
        if not db_test:
            if test_dict['status'] == 'success':
                success = 1
                fails = 0
            elif test_dict['status'] == 'fail':
                fails = 1
                success = 0
            else:
                fails = 0
                success = 0
            run_time = read_subunit.get_duration(start_time, stop_time)
            db_test = db_api.create_test(test_id, (success + fails), success,
                                         fails, run_time,
                                         session)
        else:
            test_dict['start_time'] = start_time
            test_dict['end_time'] = stop_time
            test_values = shell.increment_counts(db_test, test_dict)
            # If skipped nothing to update
            if test_values:
                db_api.update_test(test_values, db_test.id, session)
        return db_test

    def _get_attrs(self, test_id):
        attr_regex = re.compile('\[(.*)\]')
        matches = attr_regex.search(test_id)
        attrs = None
        if matches:
            attrs = matches.group(1)
        return attrs

    def _handle_test(self, test_dict):
        start, end = test_dict.pop('timestamps')
        if test_dict['status'] == 'exists' or None in (start, end):
            return
        elif test_dict['id'] == 'process-returncode':
            return
        session = self.session_factory()
        try:
            # Update the run counts
            if test_dict['status'] not in self.totals:
                self.totals[test_dict['status']] = 1
            else:
                self.totals[test_dict['status']] += 1
            values = {}
            if test_dict['status'] in ('success', 'xfail'):
                values['passes'] = self.totals['success']
            elif test_dict['status'] in ('fail', 'uxsuccess'):
                values['fails'] = self.totals['fail']
            elif test_dict['status'] == 'skip':
                values['skips'] = self.totals['skip']
            db_api.update_run(values, self.run.id, session=session)
            # Update the test totals
            db_test = self._update_test(test_dict, session, start,
                                        end)
            # Add the test run
            test_run = db_api.create_test_run(db_test.id, self.run.id,
                                              test_dict['status'],
                                              start, end,
                                              session)
            metadata = {}
            attrs = self._get_attrs(test_dict['id'])
            if attrs:
                metadata['attrs'] = attrs
            if test_dict.get('tags', None):
                metadata['tags'] = ",".join(test_dict['tags'])
            if metadata:
                db_api.add_test_run_metadata(
                    metadata, test_run.id, session)
            # TODO(mtreinish): Add attachments support to the DB.
            session.close()
        except Exception:
            session.rollback()
            raise

    def stopTestRun(self):
        self.hook.stopTestRun()
        stop_time = datetime.datetime.utcnow()
        self._subunit.seek(0)
        values = {}
        values['run_time'] = read_subunit.get_duration(self.start_time,
                                                       stop_time)
        session = self.session_factory()
        db_api.update_run(values, self.run.id, session=session)
        session.close()

    def status(self, *args, **kwargs):
        self.hook.status(*args, **kwargs)

    def get_id(self):
        return self._run_id
