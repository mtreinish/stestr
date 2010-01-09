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

"""An Argument that looks up a command object."""

from testrepository.arguments import AbstractArgument
from testrepository import commands


class CustomError(ValueError):

    def __str__(self):
        return self.args[0]

class CommandArgument(AbstractArgument):
    """An argument that looks up a command."""

    def _parse_one(self, arg):
        try:
            return commands._find_command(arg)
        except KeyError:
            raise CustomError("Could not find command '%s'." % arg)
