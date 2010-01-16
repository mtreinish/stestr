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

"""testtools.matchers.Matcher style matchers to help test testrepository."""

from testtools.matchers import Matcher, Mismatch

__all__ = ['MatchesException']


class MatchesException(Matcher):
    """Match an exc_info tuple against an exception."""

    def __init__(self, exception):
        """Create a MatchesException that will match exc_info's for exception.
        
        :param exception: An exception to check against an exc_info tuple. The
            traceback object is not inspected, only the type and arguments of
            the exception.
        """
        Matcher.__init__(self)
        self.expected = exception

    def match(self, other):
        if type(other) != tuple:
            return _StringMismatch('%r is not an exc_info tuple' % other)
        if not issubclass(other[0], type(self.expected)):
            return _StringMismatch('%r is not a %r' % (
                other[0], type(self.expected)))
        if other[1].args != self.expected.args:
            return _StringMismatch('%r has different arguments to %r.' % (
                other[1], self.expected))

    def __str__(self):
        return "MatchesException(%r)" % self.expected


class _StringMismatch(Mismatch):
    """Convenience mismatch for simply-calculated string descriptions."""

    def __init__(self, description):
        self.description = description

    def describe(self):
        return self.description
