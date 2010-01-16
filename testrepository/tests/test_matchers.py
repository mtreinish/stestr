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

"""Tests for matchers used by or for testing testrepository."""

import sys

from testrepository.tests import ResourcedTestCase
from testrepository.tests.matchers import MatchesException


class TestMatchesException(ResourcedTestCase):

    def test_does_not_match_different_exception_class(self):
        matcher = MatchesException(ValueError("foo"))
        try:
            raise Exception("foo")
        except Exception:
            error = sys.exc_info()
        mismatch = matcher.match(error)
        self.assertNotEqual(None, mismatch)
        self.assertEqual(
            "<type 'exceptions.Exception'> is not a "
            "<type 'exceptions.ValueError'>",
            mismatch.describe())

    def test_does_not_match_different_args(self):
        matcher = MatchesException(Exception("foo"))
        try:
            raise Exception("bar")
        except Exception:
            error = sys.exc_info()
        mismatch = matcher.match(error)
        self.assertNotEqual(None, mismatch)
        self.assertEqual(
            "Exception('bar',) has different arguments to Exception('foo',).",
            mismatch.describe())

    def test_matches_same_args(self):
        matcher = MatchesException(Exception("foo"))
        try:
            raise Exception("foo")
        except Exception:
            error = sys.exc_info()
        mismatch = matcher.match(error)
        self.assertEqual(None, mismatch)
