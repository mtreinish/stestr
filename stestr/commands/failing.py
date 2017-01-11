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

"""Show the current failures in the repository."""

import sys

import testtools

from stestr import output
from stestr.repository import util
from stestr import results


def get_cli_help():
    return "Show the current failures known by the repository"


def set_cli_opts(parser):
    parser.add_argument(
        "--subunit", action="store_true",
        default=False, help="Show output as a subunit stream."),
    parser.add_argument(
        "--list", action="store_true",
        default=False, help="Show only a list of failing tests."),


def _show_subunit(run):
    stream = run.get_subunit_stream()
    if getattr(sys.stdout, 'buffer', False):
        sys.stdout.buffer.write(stream.read())
    else:
        sys.stdout.write(stream.read())
    return 0


def _make_result(repo, list_tests=False):
    if list_tests:
        list_result = testtools.StreamSummary()
        return list_result, list_result
    else:
        def _get_id():
            return repo.get_latest_run().get_id()

        output_result = results.CLITestResult(_get_id,
                                              sys.stdout, None)
        summary_result = output_result.get_summary()
        return output_result, summary_result


def run(arguments):
    args = arguments[0]
    repo = util.get_repo_open(args.repo_type, args.repo_url)
    run = repo.get_failing()
    if args.subunit:
        return _show_subunit(run)
    case = run.get_test()
    failed = False
    result, summary = _make_result(repo, list_tests=args.list)
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
    if args.list:
        failing_tests = [
            test for test, _ in summary.errors + summary.failures]
        output.output_tests(failing_tests)
    return result
