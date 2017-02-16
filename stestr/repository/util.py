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

import importlib
import os
import sys


def _get_default_repo_url(repo_type):
    if repo_type == 'sql':
        repo_file = os.path.join(os.getcwd(), '.stestr.sqlite')
        repo_url = 'sqlite:///' + repo_file
    elif repo_type == 'file':
        repo_url = os.getcwd()
    else:
        raise TypeError('Unrecognized repository type %s' % repo_type)
    return repo_url


def get_repo_open(repo_type, repo_url=None):
    """Return an already initialized repo object given the parameters

    :param str repo_type: The repo module to use for the returned repo
    :param str repo_url: An optional repo url, if one is not specified the
        default $CWD/.stestr will be used.
    """
    try:
        repo_module = importlib.import_module('stestr.repository.' + repo_type)
    except ImportError:
        if repo_type == 'sql':
            print("sql repository type requirements aren't installed. To use "
                  "the sql repository ensure you installed the extra "
                  "requirements with `pip install 'stestr[sql]'`")
            sys.exit(1)
        else:
            raise
    if not repo_url:
        repo_url = _get_default_repo_url(repo_type)
    return repo_module.RepositoryFactory().open(repo_url)


def get_repo_initialise(repo_type, repo_url=None):
    """Return a newly initialized repo object given the parameters

    :param str repo_type: The repo module to use for the returned repo
    :param str repo_url: An optional repo url, if one is not specified the
        default $CWD/.stestr will be used.
    """
    try:
        repo_module = importlib.import_module('stestr.repository.' + repo_type)
    except ImportError:
        if repo_type == 'sql':
            print("sql repository type requirements aren't installed. To use "
                  "the sql repository ensure you installed the extra "
                  "requirements with `pip install 'stestr[sql]'`")
            sys.exit(1)
        else:
            raise
    if not repo_url:
        repo_url = _get_default_repo_url(repo_type)
    return repo_module.RepositoryFactory().initialise(repo_url)
