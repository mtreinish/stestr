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

"""Show the longest running tests in the repository."""

import math
from operator import itemgetter
import sys

from cliff import command

from stestr import output
from stestr.repository import util


class Slowest(command.Command):
    def get_description(self):
        help_str = """Show the slowest tests from the last test run.

        This command shows a table, with the longest running
        tests at the top.
        """
        return help_str

    def get_parser(self, prog_name):
        parser = super(Slowest, self).get_parser(prog_name)
        parser.add_argument(
            "--all", action="store_true",
            default=False, help="Show timing for all tests.")
        return parser

    def take_action(self, parsed_args):
        args = parsed_args
        return slowest(repo_type=self.app_args.repo_type,
                       repo_url=self.app_args.repo_url,
                       show_all=args.all)


def format_times(times):
    times = list(times)
    precision = 3
    digits_before_point = 1
    for time in times:
        if time[1] <= 0:
            continue
        digits_before_point = int(math.log10(time[1])) + 1
        break
    min_length = digits_before_point + precision + 1

    def format_time(time):
        # Limit the number of digits after the decimal
        # place, and also enforce a minimum width
        # based on the longest duration
        return "%*.*f" % (min_length, precision, time)
    times = [(name, format_time(time)) for name, time in times]
    return times


def slowest(repo_type='file', repo_url=None, show_all=False,
            stdout=sys.stdout):
    """Print the slowest times from the last run in the repository

    This function will print to STDOUT the 10 slowests tests in the last run.
    Optionally, using the ``show_all`` argument, it will print all the tests,
    instead of just 10. sorted by time.

    :param str repo_type: This is the type of repository to use. Valid choices
        are 'file' and 'sql'.
    :param str repo_url: The url of the repository to use.
    :param bool show_all: Show timing for all tests.
    :param file stdout: The output file to write all output to. By default
        this is sys.stdout

    :return return_code: The exit code for the command. 0 for success and > 0
        for failures.
    :rtype: int
    """

    repo = util.get_repo_open(repo_type, repo_url)
    try:
        latest_id = repo.latest_id()
    except KeyError:
        return 3
    # what happens when there is no timing info?
    test_times = repo.get_test_times(repo.get_test_ids(latest_id))
    known_times = list(test_times['known'].items())
    known_times.sort(key=itemgetter(1), reverse=True)
    if len(known_times) > 0:
        # By default show 10 rows
        if not show_all:
            known_times = known_times[:10]
        known_times = format_times(known_times)
        header = ('Test id', 'Runtime (s)')
        rows = [header] + known_times
        output.output_table(rows, output=stdout)
    return 0
