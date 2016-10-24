#
# Copyright (c) 2012 Testrepository Contributors
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

"""An Argument that gets the name of an existing path."""

import os.path

from stestr.arguments import AbstractArgument


class ExistingPathArgument(AbstractArgument):
    """An argument that stores a string verbatim."""

    def _parse_one(self, arg):
        if arg == '--':
            raise ValueError('-- is not a valid argument')
        if not os.path.exists(arg):
            raise ValueError('No such path %r' % (arg,))
        return arg
