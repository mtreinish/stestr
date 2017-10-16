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
from stestr.repository import abstract
from stestr.repository import util
from stestr import results
from stestr import subunit_trace


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
        default=False, help="Show output as a subunit stream.")
    parser.add_argument("--no-subunit-trace", action='store_true',
                        default=False,
                        help="Disable output with the subunit-trace output "
                             "filter")
    parser.add_argument('--color', action='store_true', default=False,
                        help='Enable color output in the subunit-trace output,'
                             ' if subunit-trace output is enabled. (this is '
                             'the default). If subunit-trace is disable this '
                             ' does nothing.')


def run(arguments):
    args = arguments
    pretty_out = not args.no_subunit_trace
    return last(repo_type=args.repo_type, repo_url=args.repo_url,
                subunit_out=args.subunit, pretty_out=pretty_out,
                color=args.color)


def last(repo_type='file', repo_url=None, subunit_out=False, pretty_out=True,
         color=False, stdout=sys.stdout):
    """Show the last run loaded into a a repository

    This function will print the results from the last run in the repository
    to STDOUT. It can optionally print the subunit stream for the last run
    to STDOUT if the ``subunit`` option is set to true.

    Note this function depends on the cwd for the repository if `repo_type` is
    set to file and `repo_url` is not specified it will use the repository
    located at CWD/.stestr

    :param str repo_type: This is the type of repository to use. Valid choices
        are 'file' and 'sql'.
    :param str repo_url: The url of the repository to use.
    :param bool subunit_out: Show output as a subunit stream.
    :param pretty_out: Use the subunit-trace output filter.
    :param color: Enable colorized output with the subunit-trace output filter.
    :param bool subunit: Show output as a subunit stream.
    :param file stdout: The output file to write all output to. By default
         this is sys.stdout

    :return return_code: The exit code for the command. 0 for success and > 0
        for failures.
    :rtype: int
    """
    try:
        repo = util.get_repo_open(repo_type, repo_url)
    except abstract.RepositoryNotFound as e:
        stdout.write(str(e) + '\n')
        return 1

    try:
        latest_run = repo.get_latest_run()
    except KeyError as e:
        stdout.write(str(e) + '\n')
        return 1

    if subunit_out:
        stream = latest_run.get_subunit_stream()
        output.output_stream(stream, output=stdout)
        # Exits 0 if we successfully wrote the stream.
        return 0
    case = latest_run.get_test()
    try:
        if repo_type == 'file':
            previous_run = repo.get_test_run(repo.latest_id() - 1)
        # TODO(mtreinish): add a repository api to get the previous_run to
        # unify this logic
        else:
            previous_run = None
    except KeyError:
        previous_run = None
    failed = False
    if not pretty_out:
        output_result = results.CLITestResult(latest_run.get_id, stdout,
                                              previous_run)
        summary = output_result.get_summary()
        output_result.startTestRun()
        try:
            case.run(output_result)
        finally:
            output_result.stopTestRun()
        failed = not summary.wasSuccessful()
    else:
        stream = latest_run.get_subunit_stream()
        failed = subunit_trace.trace(stream, stdout, post_fails=True,
                                     color=color)
    if failed:
        return 1
    else:
        return 0
