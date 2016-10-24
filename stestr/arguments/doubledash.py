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

"""An Argument that checks for '--'."""

from stestr.arguments import AbstractArgument


class DoubledashArgument(AbstractArgument):
    """An argument that captures '--'."""

    def __init__(self):
        super(DoubledashArgument, self).__init__('doubledash', min=0)

    def _parse_one(self, arg):
        if arg != '--':
            raise ValueError('not a doubledash %r' % (arg,))
        return arg
