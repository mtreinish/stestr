from subunit import test_results

from testtools import StreamSummary

from testrepository.utils import timedelta_to_seconds

# Subunit 0.0.8 has the time forwarding fix built-in. 0.0.8 can be detected by
# looking for _PredicateFilter.
if getattr(test_results, '_PredicateFilter', None) is None:
    class TestResultFilter(test_results.TestResultFilter):
        """Test result filter."""

        def _get_concrete_result(self):
            # XXX: This is really crappy. It assumes that the test result we
            # actually care about is decorated and that we can find our way to the
            # one we care about. We want to report counts before filtering, so we
            # should actually use two result objects - one to count and one to
            # show. Arguably also the testsRun incrementing facility should be in
            # testtools / subunit
            concrete = self
            while True:
                next = getattr(concrete, 'decorated', None)
                if next is None:
                    return concrete
                concrete = next

        def _filtered(self):
            super(TestResultFilter, self)._filtered()
            concrete = self._get_concrete_result()
            concrete.testsRun += 1

        def stopTest(self, test):
            # Filter out 'time' calls, because we want to forward those events
            # regardless of whether the test is filtered.
            #
            # XXX: Should this be pushed into subunit?
            buffered_calls = []
            for method, args, kwargs in self._buffered_calls:
                if method == 'time':
                    self.decorated.time(*args, **kwargs)
                else:
                    buffered_calls.append((method, args, kwargs))
            self._buffered_calls = buffered_calls
            super(TestResultFilter, self).stopTest(test)
else:
    TestResultFilter = test_results.TestResultFilter


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
