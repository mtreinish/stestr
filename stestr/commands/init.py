#
# Copyright (c) 2009 Testrepository Contributors
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

"""Initialise a new repository."""

import os

from stestr.repository import file as file_repo


def run(args):
    file_repo.RepositoryFactory().initialise(os.getcwd())


def set_cli_opts(parser):
    pass


def get_cli_help():
    help_str = "Create a new repository."
    return help_str
