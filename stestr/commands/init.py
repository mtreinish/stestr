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
# under the License

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
