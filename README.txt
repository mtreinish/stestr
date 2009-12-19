Test Repository
+++++++++++++++

Overview
~~~~~~~~

This project provides a database of test results which can be used as part of
developer workflow to ensure/check things like:
 * No commits without having had a test failure, test fixed cycle.
 * No commits without new tests being added.
 * What tests have failed since the last commit (to run just a subset).

Test results are inserted using subunit (and thus anything that can output
subunit or be converted into a subunit stream can be accepted).

Licensing
~~~~~~~~~

Test Repository is under BSD / Apache 2.0 licences. See the file COPYING for
details.

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
found in the doc/ directory.
