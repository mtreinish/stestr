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

"""Show the longest running tests in the repository."""

import math
from operator import itemgetter
import optparse

from testrepository.commands import Command


class slowest(Command):
    """Show the slowest tests from the last test run.

    This command shows a table, with the longest running
    tests at the top.
    """

    DEFAULT_ROWS_SHOWN = 10
    TABLE_HEADER = ('Test id', 'Runtime (s)')

    options = [
        optparse.Option(
            "--all", action="store_true",
            default=False, help="Show timing for all tests."),
        ]

    @staticmethod
    def format_times(times):
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

    def run(self):
        repo = self.repository_factory.open(self.ui.here)
        try:
            latest_id = repo.latest_id()
        except KeyError:
            return 3
        # what happens when there is no timing info?
        test_times = repo.get_test_times(repo.get_test_ids(latest_id))
        known_times = test_times['known'].items()
        known_times.sort(key=itemgetter(1), reverse=True)
        if len(known_times) > 0:
            if not self.ui.options.all:
                known_times = known_times[:self.DEFAULT_ROWS_SHOWN]
            known_times = self.format_times(known_times)
            rows = [self.TABLE_HEADER] + known_times
            self.ui.output_table(rows)
        return 0
