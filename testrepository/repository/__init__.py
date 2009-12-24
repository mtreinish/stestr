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

"""Storage of test results.

A Repository provides storage and indexing of results.

The AbstractRepository class defines the contract to which any Repository 
implementation must adhere.

The file submodule is the usual repository that code will use for local
access, and the memory submodule provides a memory only repository useful for
testing.

Repositories are identified by their URL, and new ones are made by calling
the initialize function in the appropriate repository module.
"""

class AbstractRepository(object):
    """The base class for Repository implementations.

    There are no interesting attributes or methods as yet.
    """

    @classmethod
    def initialise(klass, url):
        """Create a repository at URL. 

        Call on the class of the repository you wish to create.
        """
        raise NotImplementedError(klass.initialise)
