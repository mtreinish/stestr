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

"""Report stats about a repository. Current vestigial."""


from testrepository.commands import Command

class stats(Command):
    """Report stats about a repository.
    
    This is currently vestigial, but should grow to be the main entry point for
    getting summary information about the repository.
    """

    def run(self):
        repo = self.repository_factory.open(self.ui.here)
        self.ui.output_values([('runs', repo.count())])
        return 0
