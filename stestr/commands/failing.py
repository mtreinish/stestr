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

from cliff import command
import testtools

from stestr import output
from stestr.repository import util
from stestr import results
from stestr import user_config


class Failing(command.Command):
    def get_description(self):
        return "Show the current failures known by the repository"

    def get_parser(self, prog_name):
        parser = super(Failing, self).get_parser(prog_name)
        parser.add_argument(
            "--subunit", action="store_true",
            default=False, help="Show output as a subunit stream.")
        parser.add_argument(
            "--list", action="store_true",
            default=False, help="Show only a list of failing tests.")
        return parser

    def take_action(self, parsed_args):
        user_conf = user_config.get_user_config(self.app_args.user_config)
        args = parsed_args
        if getattr(user_conf, 'failing', False):
            list_opt = args.list or user_conf.failing.get('list', False)
        else:
            list_opt = args.list
        return failing(repo_type=self.app_args.repo_type,
                       repo_url=self.app_args.repo_url,
                       list_tests=list_opt, subunit=args.subunit)


def _show_subunit(run):
    stream = run.get_subunit_stream()
    if getattr(sys.stdout, 'buffer', False):
        sys.stdout.buffer.write(stream.read())
    else:
        sys.stdout.write(stream.read())
    return 0


def _make_result(repo, list_tests=False, stdout=sys.stdout):
    if list_tests:
        list_result = testtools.StreamSummary()
        return list_result, list_result
    else:
        def _get_id():
            return repo.get_latest_run().get_id()

        output_result = results.CLITestResult(_get_id,
                                              stdout, None)
        summary_result = output_result.get_summary()
        return output_result, summary_result


def failing(repo_type='file', repo_url=None, list_tests=False, subunit=False,
            stdout=sys.stdout):
    """Print the failing tests from the most recent run in the repository

    This function will print to STDOUT whether there are any tests that failed
    in the last run. It optionally will print the test_ids for the failing
    tests if ``list_tests`` is true. If ``subunit`` is true a subunit stream
    with just the failed tests will be printed to STDOUT.

    Note this function depends on the cwd for the repository if `repo_type` is
    set to file and `repo_url` is not specified it will use the repository
    located at CWD/.stestr

    :param str repo_type: This is the type of repository to use. Valid choices
        are 'file' and 'sql'.
    :param str repo_url: The url of the repository to use.
    :param bool list_test: Show only a list of failing tests.
    :param bool subunit: Show output as a subunit stream.
    :param file stdout: The output file to write all output to. By default
        this is sys.stdout

    :return return_code: The exit code for the command. 0 for success and > 0
        for failures.
    :rtype: int
    """
    if repo_type not in ['file', 'sql']:
        stdout.write('Repository type %s is not a type' % repo_type)
        return 1

    repo = util.get_repo_open(repo_type, repo_url)
    run = repo.get_failing()
    if subunit:
        return _show_subunit(run)
    case = run.get_test()
    failed = False
    result, summary = _make_result(repo, list_tests=list_tests)
    result.startTestRun()
    try:
        case.run(result)
    finally:
        result.stopTestRun()
    failed = not results.wasSuccessful(summary)
    if failed:
        result = 1
    else:
        result = 0
    if list_tests:
        failing_tests = [
            test for test, _ in summary.errors + summary.failures]
        output.output_tests(failing_tests, output=stdout)
    return result
