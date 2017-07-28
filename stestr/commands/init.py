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

from stestr.repository import util


def run(arguments):
    args = arguments[0]
    init(args.repo_type, args.repo_url)


def init(repo_type='file', repo_url=None):
    """Initialize a new repository

    This function will create initialize a new repostiory if one does not
    exist. If one exists the command will fail.

    Note this function depends on the cwd for the repository if `repo_type` is
    set to file and `repo_url` is not specified it will use the repository
    located at CWD/.stestr

    :param str repo_type: This is the type of repository to use. Valid choices
        are 'file' and 'sql'.
    :param str repo_url: The url of the repository to use.

    :return return_code: The exit code for the command. 0 for success and > 0
        for failures.
    :rtype: int
    """

    util.get_repo_initialise(repo_type, repo_url)


def set_cli_opts(parser):
    pass


def get_cli_help():
    help_str = "Create a new repository."
    return help_str
