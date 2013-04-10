
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
        if 'timestamp' in kwargs:
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
