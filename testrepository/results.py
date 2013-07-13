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


from testtools import StreamSummary

from testrepository.utils import timedelta_to_seconds


class SummarizingResult(StreamSummary):

    def __init__(self):
        super(SummarizingResult, self).__init__()

    def startTestRun(self):
        super(SummarizingResult, self).startTestRun()
        self._first_time = None
        self._last_time = None

    def status(self, *args, **kwargs):
        if kwargs.get('timestamp') is not None:
            timestamp = kwargs['timestamp']
            if self._last_time is None:
                self._first_time = timestamp
                self._last_time = timestamp
            if timestamp < self._first_time:
                self._first_time = timestamp
            if timestamp > self._last_time:
                self._last_time = timestamp
        super(SummarizingResult, self).status(*args, **kwargs)

    def get_num_failures(self):
        return len(self.failures) + len(self.errors)

    def get_time_taken(self):
        if None in (self._last_time, self._first_time):
            return None
        return timedelta_to_seconds(self._last_time - self._first_time)
