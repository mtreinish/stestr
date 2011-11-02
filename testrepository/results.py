from datetime import timedelta

from subunit import test_results

from testtools import TestResult


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


class SummarizingResult(TestResult):

    def __init__(self):
        super(SummarizingResult, self).__init__()
        self.num_failures = 0
        self._first_time = None

    def startTestRun(self):
        super(SummarizingResult, self).startTestRun()
        self.num_failures = 0
        self._first_time = None

    def get_num_failures(self):
        return len(self.failures) + len(self.errors)

    def time(self, a_time):
        if self._first_time is None:
            self._first_time = a_time
        super(SummarizingResult, self).time(a_time)

    def get_time_taken(self):
        now = self._now()
        if None in (self._first_time, now):
            return None
        return now - self._first_time
