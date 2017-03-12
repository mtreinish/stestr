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

"""Load data into a repository."""


import functools
import sys

import subunit
import testtools

from stestr import output
from stestr.repository import abstract as repository
from stestr.repository import util
from stestr import results
from stestr import utils


def set_cli_opts(parser):
    parser.add_argument("--partial", action="store_true",
                        default=False,
                        help="The stream being loaded was a partial run.")
    parser.add_argument("--force-init", action="store_true",
                        default=False,
                        help="Initialise the repository if it does not exist "
                             "already")
    parser.add_argument("--subunit", action="store_true",
                        default=False,
                        help="Display results in subunit format.")
    parser.add_argument("--id", "-i", default=None,
                        help="Append the stream into an existing entry in the "
                             "repository")


def get_cli_help():
    help_str = """Load a subunit stream into a repository.

        Failing tests are shown on the console and a summary of the stream is
        printed at the end.

        Unless the stream is a partial stream, any existing failures are
        discarded.
        """
    return help_str


class InputToStreamResult(object):
    """Generate Stream events from stdin.

    Really a UI responsibility?
    """

    def __init__(self, stream):
        self.source = stream
        self.stop = False

    def run(self, result):
        while True:
            if self.stop:
                return
            char = self.source.read(1)
            if not char:
                return
            if char == b'a':
                result.status(test_id='stdin', test_status='fail')


def run(arguments):
    load(arguments)


def load(arguments, in_streams=None, partial=False, subunit_out=False,
         repo_type=None, repo_url=None, run_id=None):
    args = arguments[0]
    streams = arguments[1]
    if args:
        repo_type = args.repo_type
        repo_url = args.repo_url
    try:
        repo = util.get_repo_open(repo_type, repo_url)
    except repository.RepositoryNotFound:
        if args.force_init:
            repo = util.get_repo_initialise(repo_type, repo_url)
        else:
            raise
    # Not a full implementation of TestCase, but we only need to iterate
    # back to it. Needs to be a callable - its a head fake for
    # testsuite.add.
    if in_streams:
        streams = utils.iter_streams(in_streams, 'subunit')
    elif streams:
        opener = functools.partial(open, mode='rb')
        streams = map(opener, streams)
    else:
        streams = [sys.stdin.buffer]

    def mktagger(pos, result):
        return testtools.StreamTagger([result], add=['worker-%d' % pos])

    def make_tests():
        for pos, stream in enumerate(streams):
            # Calls StreamResult API.
            case = subunit.ByteStreamToStreamResult(
                stream, non_subunit_name='stdout')
            decorate = functools.partial(mktagger, pos)
            case = testtools.DecorateTestCaseResult(case, decorate)
            yield (case, str(pos))

    case = testtools.ConcurrentStreamTestSuite(make_tests)
    # One unmodified copy of the stream to repository storage
    _partial = False
    if args:
        _partial = getattr(args, 'partial')
    # Set partial_stream if it comes in via the CLI or the kwarg
    partial_stream = _partial or partial
    _subunit = False
    if args:
        _subunit = getattr(args, 'subunit')
    _subunit_out = _subunit or subunit_out
    _run_id = None
    if args:
        _run_id = getattr(args, 'id')
    _run_id = _run_id or run_id
    if not _run_id:
        inserter = repo.get_inserter(partial=partial_stream)
    else:
        inserter = repo.get_inserter(partial=partial_stream, run_id=_run_id)
    if _subunit_out:
        output_result, summary_result = output.make_result(inserter.get_id)
    else:
        try:
            previous_run = repo.get_latest_run()
        except KeyError:
            previous_run = None
        output_result = results.CLITestResult(
            inserter.get_id, sys.stdout, previous_run)
        summary_result = output_result.get_summary()
    result = testtools.CopyStreamResult([inserter, output_result])
    result.startTestRun()
    try:
        case.run(result)
    finally:
        result.stopTestRun()
    if not summary_result.wasSuccessful():
        return 1
    else:
        return 0
