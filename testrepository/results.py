from subunit import test_results
from testrepository.ui import BaseUITestResult


class TestResultFilter(test_results.TestResultFilter):
    """Test result filter."""

    def _filtered(self):
        super(TestResultFilter, self)._filtered()
        # XXX: This is really crappy. It assumes that the test result we
        # actually care about is decorated and that we can find our way to the
        # one we care about. We want to report counts before filtering, so we
        # should actually use two result objects - one to count and one to
        # show.
        concrete = self.decorated
        while not isinstance(concrete, BaseUITestResult):
            concrete = concrete.decorated
        concrete.testsRun += 1
