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

"""'Arguments' for testr.

This is a small typed arguments concept - which is perhaps obsoleted by
argparse in Python 2.7, but for testrepository is an extension used with
optparse.

The code in this module contains the AbstractArgument base class. Individual
argument types are present in e.g. testrepository.arguments.string.

Plugins and extensions wanting to add argument types should either define them
internally or install into testrepository.arguments as somename (perhaps by
extending the testrepository.arguments __path__ to include a directory
containing their argument types - no __init__ is needed in that directory.)
"""


class AbstractArgument(object):
    """A argument that a command may need.

    Arguments can be converted into a summary for describing the UI to users,
    and provide validator/parsers for the arguments.

    :ivar: The name of the argument. This is used for retrieving the argument
        from UI objects, and for generating the summary.
    """

    def __init__(self, name, min=1, max=1):
        """Create an AbstractArgument.

        While conceptually a separate SequenceArgument could be used, all
        arguments support sequencing to avoid unnecessary boilerplate in user
        code.

        :param name: The name for the argument.
        :param min: The minimum number of occurences permitted.
        :param max: The maximum number of occurences permitted. None for
            unlimited.
        """
        self.name = name
        self.minimum_count = min
        self.maximum_count = max

    def summary(self):
        """Get a regex-like summary of this argument."""
        result = self.name
        if (self.minimum_count == self.maximum_count and
            self.minimum_count == 1):
                return result
        minmax = (self.minimum_count, self.maximum_count)
        if minmax == (0, 1):
            return result + '?'
        if minmax == (1, None):
            return result + '+'
        if minmax == (0, None):
            return result + '*'
        if minmax[1] == None:
            minmax = (minmax[0], '')
        return result + '{%s,%s}' % minmax

    def parse(self, argv):
        """Evaluate arguments in argv.

        :param argv: The arguments to parse.
        :return: The parsed results as a list.
        """
        raise NotImplementedError(self.parse)
