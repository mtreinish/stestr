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

"""Get a quickstart on testrepository."""

from testrepository.commands import Command

class quickstart(Command):
    """Introductory documentation for testrepository."""

    def run(self):
        # This gets written to README.txt by Makefile.
        help = """Test Repository
+++++++++++++++

Overview
~~~~~~~~

This project provides a database of test results which can be used as part of
developer workflow to ensure/check things like:

* No commits without having had a test failure, test fixed cycle.
* No commits without new tests being added.
* What tests have failed since the last commit (to run just a subset).
* What tests are currently failing and need work.

Test results are inserted using subunit (and thus anything that can output
subunit or be converted into a subunit stream can be accepted).

A mailing list for discussion, usage and development is at
https://launchpad.net/~testrepository-dev - all are welcome to join. Some folk
hang out on #testrepository on irc.freenode.net.

CI for the project is at http://build.robertcollins.net/job/testrepository-default/.

Licensing
~~~~~~~~~

Test Repository is under BSD / Apache 2.0 licences. See the file COPYING in the source for details.

Quick Start
~~~~~~~~~~~

Create a repository::
  $ testr init

Load a test run into the repository::
  $ testr load < testrun

Query the repository::
  $ testr stats
  $ testr last
  $ testr failing

Delete a repository::
  $ testr delete

Documentation
~~~~~~~~~~~~~

More detailed documentation including design and implementation details, a
user manual, and guidelines for development of Test Repository itself can be
found at https://testrepository.readthedocs.org/en/latest, or in the source
tree at doc/ (run make -C doc html).
"""
        self.ui.output_rest(help)
        return 0
