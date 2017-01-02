Slim/Super Test Repository
==========================

You can see the full rendered docs at: http://stestr.readthedocs.io/en/latest/

Overview
--------

stestr is a fork of the `testrepository`_ that strips out a lot of the cruft
from the testr project and concentrates on being a fast dedicated test runner
runner. This is the usage of testr that everyone expects testr to be. The code
base is also designed to be a lot more explicit and providing a useful python
api that is documented and has examples. Gone are the factory of factories and
the abstraction of abstractions that are difficult to follow. stestr is also
only a python test runner, so some of the generic abstractions which enabled
testr to work with any subunit emitting runner are gone. stestr hard codes
python-subunit-isms into how it works.

.. _testrepository: https://testrepository.readthedocs.org/en/latest

While stestr was originally forked from testrepository it is not 100% backwards
compatible with testrepository. At a high level the basic concepts of operation
are shared between the 2 projects but the actual usage between the 2 is not
exactly the same.

Using stestr
------------

After you install stestr to use it to run tests is pretty straightforward. The
first thing you'll need to do is create a .stestr.conf file for your project.
This file is used to tell stestr where to find tests and basic information
about how tests are run. A basic minimal example of the contesnts of this is::

  [DEFAULT]
  test_path=./project_source_dir/tests

which just tells stestr the relative path for the directory to use for
test discovery. This is the same as --start-directory in the standard `unittest
discovery`_

.. _unittest discovery: https://docs.python.org/2.7/library/unittest.html#test-discovery

After this file is created you should be all set to start using stestr to run
tests. You can create a repository for test results with the stestr init
command, just run::

    stestr init

and it will create a .stestr directory in your cwd that will be used to store
test run results. (if you run stestr run it will create this if it doesn't
exist) Then to run tests just use::

    stestr run

it will then execute all the tests found by test discovery. For all the details
on these commands and more thorough explanation of options see the
:ref:`manual`.
