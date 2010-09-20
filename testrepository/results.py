from subunit import test_results


class TestResultFilter(test_results.TestResultFilter):
    """Test result filter."""

    def _filtered(self):
        super(TestResultFilter, self)._filtered()
        # XXX: This is really crappy. It assumes that the test result we
        # actually care about is decorated twice. Probably the more correct
        # thing to do is fix subunit so that incrementing 'testsRun' on a test
        # result increments them on the decorated test result.
        self.decorated.decorated.testsRun += 1

    def addSkip(self, test, reason=None, details=None):
        super(TestResultFilter, self).addSkip(test, reason=reason, details=details)
        self.decorated.decorated.skip_reasons[]
