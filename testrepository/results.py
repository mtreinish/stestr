from subunit import test_results


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
        buffered_calls = []
        for method, args, kwargs in self._buffered_calls:
            if method == 'time':
                self.decorated.time(*args, **kwargs)
            else:
                buffered_calls.append((method, args, kwargs))
        self._buffered_calls = buffered_calls
        super(TestResultFilter, self).stopTest(test)
