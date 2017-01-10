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

from stestr import output
from stestr.repository import util


def get_cli_help():
    help_str = """Show the slowest tests from the last test run.

    This command shows a table, with the longest running
    tests at the top.
    """
    return help_str


def set_cli_opts(parser):
    parser.add_argument(
        "--all", action="store_true",
        default=False, help="Show timing for all tests."),


def format_times(times):
    times = list(times)
    precision = 3
    digits_before_point = int(
        math.log10(times[0][1])) + 1
    min_length = digits_before_point + precision + 1

    def format_time(time):
        # Limit the number of digits after the decimal
        # place, and also enforce a minimum width
        # based on the longest duration
        return "%*.*f" % (min_length, precision, time)
    times = [(name, format_time(time)) for name, time in times]
    return times


def run(args):
    repo = util.get_repo_open(args[0].repo_type, args[0].repo_url)
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
        if not args[0].all:
            known_times = known_times[:10]
        known_times = format_times(known_times)
        header = ('Test id', 'Runtime (s)')
        rows = [header] + known_times
        output.output_table(rows)
    return 0
