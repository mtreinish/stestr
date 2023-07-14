# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Initialise a new repository."""

import errno
import sys

from cliff import command

from stestr.repository import util


class Init(command.Command):
    """Create a new repository."""

    def take_action(self, parsed_args):
        init(self.app_args.repo_url)


def init(repo_url=None, stdout=sys.stdout):
    """Initialize a new repository

    This function will create initialize a new repostiory if one does not
    exist. If one exists the command will fail.

    Note this function depends on the cwd for the repository if `repo_url` is
    not specified it will use the repository located at CWD/.stestr

    :param str repo_url: The url of the repository to use.

    :return return_code: The exit code for the command. 0 for success and > 0
        for failures.
    :rtype: int
    """
    try:
        util.get_repo_initialise(repo_url=repo_url)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
        repo_path = repo_url or "./stestr"
        stdout.write(
            "The specified repository directory %s already exists. "
            "Please check if the repository already exists or "
            "select a different path\n" % repo_path
        )
        return 1
