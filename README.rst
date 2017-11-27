Slim/Super Test Repository
==========================

.. image:: https://travis-ci.org/mtreinish/stestr.svg?branch=master
    :target: https://travis-ci.org/mtreinish/stestr

.. image:: https://coveralls.io/repos/github/mtreinish/stestr/badge.svg?branch=master
    :target: https://coveralls.io/github/mtreinish/stestr?branch=master

.. image:: https://img.shields.io/pypi/v/stestr.svg
    :target: https://pypi.python.org/pypi/stestr

You can see the full rendered docs at: http://stestr.readthedocs.io/en/latest/

Overview
--------

stestr is a fork of the `testrepository`_ that concentrates on being a
dedicated test runner for python projects. The generic abstraction
layers which enabled testr to work with any subunit emitting runner are gone.
stestr hard codes python-subunit-isms into how it works. The code base is also
designed to try and be explicit, and to provide a python api that is documented
and has examples.

.. _testrepository: https://testrepository.readthedocs.org/en/latest

While stestr was originally forked from testrepository it is not 100% backwards
compatible with testrepository. At a high level the basic concepts of operation
are shared between the 2 projects but the actual usage between the 2 is not
exactly the same.

Installing stestr
-----------------

stestr is available via pypi, so all you need to do is run::

  pip install -U stestr

to get stestr on your system. If you need to use a development version of
stestr you can clone the repo and install it locally with::

  git clone https://github.com/mtreinish/stestr.git && pip install -e stestr

which will install stestr in your python environment in editable mode for local
development

Using stestr
------------

After you install stestr to use it to run tests is pretty straightforward. The
first thing you'll need to do is create a ``.stestr.conf`` file for your
project. This file is used to tell stestr where to find tests and basic
information about how tests are run. A basic minimal example of the
contents of this is::

  [DEFAULT]
  test_path=./project_source_dir/tests

which just tells stestr the relative path for the directory to use for
test discovery. This is the same as ``--start-directory`` in the standard
`unittest discovery`_

.. _unittest discovery: https://docs.python.org/2.7/library/unittest.html#test-discovery

After this file is created you should be all set to start using stestr to run
tests. You can create a repository for test results with the stestr init
command, just run::

    stestr init

and it will create a .stestr directory in your cwd that will be used to store
test run results. (if you run stestr run it will create this if it doesn't
exist) Then to run tests just use::

    stestr run

it will then execute all the tests found by test discovery. If you're just
running a single test (or module) and want to avoid the overhead of doing test
discovery you can use the ``--no-discover``/``-n`` option.

For all the details on these commands and more thorough explanation of options
see the :ref:`manual`.

Migrating from testrepository
-----------------------------

If you have a project that is already using testrepository stestr's source repo
contains a helper script for migrating your repo to use stestr. This script
just creates a ``.stestr.conf`` file from a ``.testr.conf`` file.
(assuming it uses a standard subunit.run test command format) To run
this from your project repo just call::

    $STESTR_SOURCE_DIR/tools/testr_to_stestr.py

and you'll have a ``.stestr.conf`` created.
