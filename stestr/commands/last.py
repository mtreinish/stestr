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

"""Show the last run loaded into a repository."""

import sys

from stestr import output
from stestr.repository import util
from stestr import results


def get_cli_help():
    help_str = """Show the last run loaded into a repository.

    Failing tests are shown on the console and a summary of the run is printed
    at the end.

    Without --subunit, the process exit code will be non-zero if the test run
    was not successful. With --subunit, the process exit code is non-zero if
    the subunit stream could not be generated successfully.
    """
    return help_str


def set_cli_opts(parser):
    parser.add_argument(
        "--subunit", action="store_true",
        default=False, help="Show output as a subunit stream."),


def run(arguments):
    args = arguments[0]
    repo = util.get_repo_open(args.repo_type, args.repo_url)
    latest_run = repo.get_latest_run()
    if args.subunit:
        stream = latest_run.get_subunit_stream()
        output.output_stream(stream)
        # Exits 0 if we successfully wrote the stream.
        return 0
    case = latest_run.get_test()
    try:
        previous_run = repo.get_test_run(repo.latest_id() - 1)
    except KeyError:
        previous_run = None
    failed = False
    output_result = results.CLITestResult(latest_run.get_id, sys.stdout,
                                          previous_run)
    summary = output_result.get_summary()
    output_result.startTestRun()
    try:
        case.run(output_result)
    finally:
        output_result.stopTestRun()
    failed = not summary.wasSuccessful()
    if failed:
        return 1
    else:
        return 0
