#
# Copyright (c) 2010 Testrepository Contributors
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

"""Show the current failures in the repository."""

import os
import sys

import testtools

from stestr import output
from stestr.repository import file as file_repo


def get_cli_help():
    pass


def set_cli_opts(parser):
    parser.add_argument(
        "--subunit", action="store_true",
        default=False, help="Show output as a subunit stream."),
    parser.add_argument(
        "--list", action="store_true",
        default=False, help="Show only a list of failing tests."),


def _show_subunit(run):
    stream = run.get_subunit_stream()
    sys.stdout.write(stream.read())
    return 0


def _make_result(repo, list_tests=False):
    if list_tests:
        list_result = testtools.StreamSummary()
        return list_result, list_result
    else:
        return output.make_result(repo.latest_id)


def run(args):
    # TODO(mtreinish): Add a CLI opt to set different repo types
    repo = file_repo.RepositoryFactory().open(os.getcwd())
    run = repo.get_failing()
    if args[0].subunit:
        return _show_subunit(run)
    case = run.get_test()
    failed = False
    result, summary = _make_result(repo)
    result.startTestRun()
    try:
        case.run(result)
    finally:
        result.stopTestRun()
    failed = not summary.wasSuccessful()
    if failed:
        result = 1
    else:
        result = 0
    if args[0].list:
        failing_tests = [
            test for test, _ in summary.errors + summary.failures]
        output.output_tests(failing_tests)
    return result
