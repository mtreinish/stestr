.. _manual:

stestr user manual
==================

Usage
-----

.. autoprogram-cliff:: stestr.cli.StestrCLI
   :application: stestr

.. autoprogram-cliff:: stestr.cm
   :application: stestr

Overview
--------

stestr is an application for running and tracking test results. Any test run
that can be represented as a subunit stream can be inserted into a repository.
However, the test running mechanism assumes python is being used. It is
originally forked from the testrepository project so the usage is similar.

A typical basic example workflow is::

  # Create a store to manage test results in.
  $ stestr init
  # Do a test run
  $ stestr run

Most commands in testr have comprehensive online help, and the commands::

  $ stestr --help
  $ stestr [command] --help

Will be useful to explore the system.

Configuration
-------------

To configure stestr for a project you can write a stestr configuration file.
This lets you set basic information about how tests are run for a project.
By default the config file needs to be ``.stestr.conf`` in the same directory
that stestr is run from, normally the root of a project's repository. However,
the ``--config``/``-c`` CLI argument can specify an alternate path for it.

The 2 most important options in the stestr config file are ``test_path``
and ``top_dir``. These 2 options are used to set the `unittest discovery`_
options for stestr. (test_path is the same as ``--start-directory``
and top_dir is the same as ``--top-level-directory`` in the doc) Only test_path
is a required field in the config file, if top_dir is not specified it defaults
to ``./``. It's also worth noting that shell variables for these 2 config
options (and only these 2 options) are expanded on platforms that have a shell.
This enables you to have conditional discovery paths based on your environment.

.. _unittest discovery: https://docs.python.org/3/library/unittest.html#test-discovery

For example, having a config file like::

    [DEFAULT]
    test_path=${TEST_PATH:-./foo/tests}

will let you override the discovery start path using the TEST_PATH environment
variable.

A full example config file is::

  [DEFAULT]
  test_path=./project/tests
  top_dir=./
  group_regex=([^\.]*\.)*
  runner=pytest


The ``group_regex`` option is used to specify is used to provide a scheduler
hint for how tests should be divided between test runners. See the
:ref:`group_regex` section for more information on how this works.
You can also specify the ``parallel_class=True`` instead of
group_regex to group tests in the stestr scheduler together by
class. Since this is a common use case this enables that without
needing to memorize the complicated regex for ``group_regex`` to do
this. The ``runner`` argument is used to specify the test runner to use. By
default a runner based on Python's standard library ``unittest`` module is
used. However, if you'd prefer to use ``pytest`` as your runner you can specify
this as the runner argument in the config file.

There is also an option to specify all the options in the config file via the
CLI. This way you can run stestr directly without having to write a config file
and manually specify the test_path like above with the ``--test-path``/``-t``
CLI argument.

.. _tox:

Tox
'''

If you are also using `tox <https://tox.readthedocs.io/en/latest/>`__ with your
project then it is not necessary to create separate stestr config file, instead
you can embed the necessary configuration in the existing ``tox.ini`` file with
an ``[stestr]`` section. For example a full configuration section would be::

  [stestr]
  test_path=./project/tests
  top_dir=./
  group_regex=([^\.]*\.)*

Any configuration directives outside the ``[stestr]`` section will be ignored.
It's important to note that if either the ``--config``/``-c`` CLI argument is
specified, or the default location ``.stestr.conf`` file is present
then any configuration in the ``tox.ini`` will be ignored. Configuration
embedded in a ``tox.ini`` will only be used if other configuration
files are not present.

pyproject.toml
''''''''''''''

Similarly, if your project is using ``pyproject.toml``, you may forego the
config file, and instead create a ``[tool.stestr]`` section with the desired
configuration options.  For example::

  [tool.stestr]
  test_path = "./project/tests"
  top_dir = "./"
  group_regex = "([^\.]*\.)*"

The same caveats apply as the :ref:`tox` with regards to CLI arguments.

Configuration file precedence
'''''''''''''''''''''''''''''

The order in which configuration files are read is as follows:

* Any file specified with the ``--config``/``-c`` CLI argument
* The ``.stestr.conf`` file
* The ``[tool.stestr]`` section in a ``pyproject.toml`` file
* The ``[stestr]`` section in a ``tox.ini`` file

Also of note is that files specified with ``--config-file``/``-c``
may be either ``.ini`` or TOML format. If providing configs in
``.ini`` format, they **must** be in a ``[DEFAULT]`` section. If
providing configs in TOML format, the configuration directives
**must** be located in a ``[tool.stestr]`` section, and the filename
**must** have a ``.toml`` extension.



Running tests
-------------

To run tests the ``stestr run`` command is used. By default this will run all
tests discovered using the discovery parameters in the stestr config file.

If you'd like to avoid the overhead of test discovery and just manually execute
a single test (test class, or module) you can do this using the
``--no-discover``/``-n`` option. For example::

  $ stestr run --no-discover project.tests.test_foo.TestFoo

you can also give it a file path and stestr will convert that to the proper
python path under the covers. (assuming your project don't manually mess with
import paths) For example::

  $ stestr run --no-discover project/tests/test_foo.py

will also bypass discovery and directly call the test runner on the module
specified.

Additionally you can specify a specific class or method within that file using
``::`` to specify a class and method. For example::

  $ stestr run --no-discover project/tests/test_foo.py::TestFoo::test_method

will skip discovery and directly call the test runner on the test method in the
specified test class.

Test runners
''''''''''''

By default ``stestr`` is built to run tests leveraging the Python standard
library ``unittest`` modules runner. stestr includes a test runner that will
emit the subunit protocol it relies on internally to handle live results from
parallel workers. However, there is an alternative runner available that
leverages ``pytest`` which is a popular test runner and testing library
alternative to the standard library's ``unittest`` module. The ``stestr``
project bundles a ``pytest`` plugin that adds real time subunit output to
pytest. As a test suite author the ``pytest`` plugin enables you to write your
test suite using pytest's test library instead of ``unittest``. There are two
ways to specify your test runner, first is the ``--pytest`` flag on
``stestr run``. This tells stestr for this test run use ``pytest`` as the runner
instead of ``unittest``, this is good for a/b comparisons between the test
runners and also general investigations with using different test runners. The
other option is to leverage your project's config file and set the ``runner``
field to either ``pytest`` or ``unittest`` (although ``unittest`` is always the
default so you shouldn't ever need to set it). This is the more natural fit
because if your test suite is written using pytest it won't be compatible with
the unittest based runner.

Running with pdb
''''''''''''''''

If you'd like to run pdb during the execution of the tests you should use the
``--pdb`` flag on ``stestr run``. This flag behaves the same way as the
``--no-discover`` flag except that it does not launch an external process to
run the tests. This enables pdb to work as expected without any issues with the
tradeoff that output from the test runner will occur after tests have finished
execution.

It's also worth noting that if you are using a fixture to capture stdout (which
is a common practice for parallel test excecution) you'll likely want to
disable that fixture when running with pdb. Those fixtures can often interfere
with pdb's output and will sometimes capture output from pdb.

Test Selection
--------------

Arguments passed to ``stestr run`` are used to filter test ids that will be
run. stestr will perform unittest discovery to get a list of all test ids and
then apply each argument as a regex filter. Tests that match any of the given
filters will be run. For example, if you called ``stestr run foo bar`` this
will only run the tests that have a regex match with foo **or** a regex match
with bar.

stestr allows you do to do simple test exclusion via passing a
exclusion regexp::

  $ stestr run --exclude-regex 'slow_tests|bad_tests'

stestr also allow you to combine these arguments::

  $ stestr run --exclude-regex 'slow_tests|bad_tests' ui\.interface

Here first we selected all tests which matches to ``ui\.interface``, then we
are dropping all test which matches ``slow_tests|bad_tests`` from the final
list.

stestr also allows you to specify an exclusion list file to define a set of
regexes to exclude. You can specify an exclusion list file with the
``--exclude-list``/``-e`` option, for example::

  $ stestr run --exclude-list $path_to_file

The format for the file is line separated regex, with ``#`` used to signify the
start of a comment on a line. For example::

  # Exclusion list File
  ^regex1 # Excludes these tests
  .*regex2 # exclude those tests

The regexp used in the exclusion list file or passed as argument, will be used
to drop tests from the initial selection list. It will generate a list which
will exclude any tests matching ``^regex1`` or ``.*regex2``. If an exclusion
list file is used in conjunction with the normal filters then the regex filters
passed in as an argument regex will be used for the initial test selection, and
the exclusion regexes from the exclusion list file on top of that.

The dual of the exclusion list file is the inclusion list file which will
include any tests matching the regexes in the file. You can specify the path to
the file with ``--include-list``/``-i``, for example::

  $ stestr run --include-list $path_to_file

The format for the file is more or less identical to the exclusion list file::

  # Inclusion list File
  ^regex1 # Include these tests
  .*regex2 # include those tests

However, instead of excluding the matches it will include them.

It's also worth noting that you can use the test list option to dry run any
selection arguments you are using. You just need to use ``stestr list``
with your selection options to do this, for example::

  $ stestr list 'regex3.*' --exclude-list exclusion_list.txt

This will list all the tests which will be run by stestr using that combination
of arguments.

Adjusting test run output
-------------------------

By default the ``stestr run`` command uses an output filter called
subunit-trace. (as does the ``stestr last`` command) This displays the tests
as they are finished executing, as well as their worker and status. It also
prints aggregate numbers about the run at the end. You can read more about
subunit-trace in the module doc: :ref:`subunit_trace`.

However, the test run output is configurable, you can disable this output
with the ``--no-subunit-trace`` flag which will be completely silent except for
any failures it encounters. There is also the ``--color`` flag which will
enable colorization with subunit-trace output. If you prefer to deal with the
raw subunit yourself and run your own output rendering or filtering you can use
the ``--subunit`` flag to output the result stream as raw subunit v2.

There is also an ``--abbreviate`` flag available, when this is used a single
character is printed for each test as it is executed. A ``.`` is printed for a
successful test, a ``F`` for a failed test, and a ``S`` for a skipped test.

In the default subunit-trace output any captured output to stdout and stderr is
printed after test execution, for both successful and failed tests. However,
in some cases printing these attachments on a successful tests is not the
preferred behavior. You can use the ``--suppress-attachments`` flag to disable
printing stdout or stderr attachments for successful tests.

While by default attachments for captured stdout and stderr are printed, it
is also possible that a test has other text attachments (a common example is
python logging) which are not printed on successful test execution, only on
failures. If you would like to have these attachments also printed for
successful tests you can use the ``--all-attachments`` flag to print all text
attachments on both successful and failed tests. Both ``--all-attachments``
and ``--suppress-attachments`` can not be set at the same time. If both are
set in the user config file then the ``suppress-attachments`` flag will take
priority and no attachments will be printed for successful tests. If either
``--suppress-attachments`` or ``--all-attachments`` is set via the CLI it
will take precedence over matching options set in the user config file.

Combining Test Results
----------------------
There is sometimes a use case for running a single test suite split between
multiple invocations of the stestr run command. For example, running a subset
of tests with a different concurrency. In these cases you can use the
``--combine`` flag on ``stestr run``. When this flag is specified stestr will
append the subunit stream from the test run into the most recent entry in the
repository.

Alternatively, you can manually load the test results from a subunit stream
into an existing test result in the repository using the ``--id``/``-i`` flag
on the ``stestr load`` command. This will append the results from the input
subunit stream to the specified id.


Running previously failed tests
-------------------------------

``stestr run`` also enables you to run just the tests that failed in the
previous run. To do this you can use the ``--failing`` argument.

A common workflow using this is:

#. Run tests (and some fail)::

    $ stestr run

#. Fix currently broken tests - repeat until there are no failures::

    $ stestr run --failing

#. Do a full run to find anything that regressed during the reduction process::

      $ stestr run

Another common use case is repeating a failure that occurred on a remote
machine (e.g. during a jenkins test run). There are a few common ways to do
approach this.

Firstly, if you have a subunit stream from the run you can just load it::

  $ stestr load < failing-stream

and then run the tests which failed from that loaded run::

  $ stestr run --failing

If using a file type repository (which is the default) the streams generated
by test runs are in the repository path, which defaults to *.stestr/* in the
working directory, and stores the stream in a file named for their run id -
e.g. .stestr/0 is the first run.

.. note::
    For right now these files are stored in the subunit v1 format, but all of
    the stestr commands, including load, only work with the subunit v2 format.
    This can be converted using the **subunit-1to2** tool in the
    `python-subunit`_ package.

.. _python-subunit: https://pypi.org/project/python-subunit/

If you have access to the remote machine you can also get the subunit stream
by running::

  $ stestr last --subunit > failing-stream

This is often a bit easier than trying to manually pull the stream file out
of the .stestr directory. (also it will be in the subunit v2 format already)

If you do not have a stream or access to the machine you may be able to use a
list file. If you can get a file that contains one test id per line, you can
run the named tests like this::

  $ stestr run --load-list FILENAME

This can also be useful when dealing with sporadically failing tests, or tests
that only fail in combination with some other test - you can bisect the tests
that were run to get smaller and smaller (or larger and larger) test subsets
until the error is pinpointed.

``stestr run --until-failure`` will run your test suite again and again and
again stopping only when interrupted or a failure occurs. This is useful
for repeating timing-related test failures.

Listing tests
-------------

To see a list of tests found by stestr you can use the ``stestr list`` command.
This will list all tests found by discovery.

You can also use this to see what tests will be run by a given stestr run
command. For instance, the tests that ``stestr run myfilter`` will run are
shown by ``stestr list myfilter``. As with the run command, arguments to list
are used to regex filter the tests.

Parallel testing
----------------

stestr lets you run tests in parallel by default. So, it actually does this by
def::

  $ stestr run

This will first list the tests, partition the tests into one partition per CPU
on the machine, and then invoke multiple test runners at the same time, with
each test runner getting one partition. Currently the partitioning algorithm
is simple round-robin for tests that stestr has not seen run before, and
equal-time buckets for tests that stestr has seen run.

To determine how many CPUs are present in the machine, stestr will
use the multiprocessing Python module On operating systems where this is not
implemented, or if you need to control the number of workers that are used,
the ``--concurrency`` option will let you do so::

  $ stestr run --concurrency=2

When running tests in parallel, stestr adds a tag for each test to the subunit
stream to show which worker executed that test. The tags are of the form
``worker-%d`` and are usually used to reproduce test isolation failures, where
knowing exactly what test ran on a given worker is important. The %d that is
substituted in is the partition number of tests from the test run - all tests
in a single run with the same worker-N ran in the same test runner instance.

To find out which slave a failing test ran on just look at the 'tags' line in
its test error::

  ======================================================================
  label: testrepository.tests.ui.TestDemo.test_methodname
  tags: foo worker-0
  ----------------------------------------------------------------------
  error text

And then find tests with that tag::

  $ stestr last --subunit | subunit-filter -s --xfail --with-tag=worker-3 | subunit-ls > slave-3.list

.. _group_regex:

Grouping Tests
--------------

In certain scenarios you may want to group tests of a certain type together so
that they will be run by the same worker process. The ``group_regex`` option in
the stestr config file permits this. When set, tests are grouped by the entire
matching portion of the regex. The match must begin at the start of the string.
Tests with no match are not grouped.

For example, setting the following option in the stestr config file will group
tests in the same class together (the last '.' splits the class and test
method)::

    group_regex=([^\.]+\.)+

However, because grouping tests at the class level is a common use
case there is also a config option, ``parallel_class``, to do
this. For example, you can use::

    parallel_class=True

and it will group tests in the same class together.

.. note::
   This ``parallel_class`` option takes priority over the
   ``group_regex`` option. And if both on the CLI and in the config
   are set, we use the option on the CLI not in a config file. For
   example, ``--group-regex`` on the CLI and ``parallel-class`` in a
   config file are set, ``--group-regex`` is higer priority than
   ``parallel-class`` in this case.

Test Scheduling
---------------
By default stestr schedules the tests by first checking if there is any
historical timing data on any tests. It then sorts the tests by that timing
data loops over the tests in order and adds one to each worker that it will
launch. For tests without timing data, the same is done, except the tests are
in alphabetical order instead of based on timing data. If a group regex is used
the same algorithm is used with groups instead of individual tests.

However there are options to adjust how stestr will schedule tests. The primary
option to do this is to manually schedule all the tests run. To do this use the
``--worker-file`` option for stestr run. This takes a path to a yaml file that
instructs stestr how to run tests. It is formatted as a list of dicts with a
single element each with a list describing the tests to run on each worker. For
example::

    - worker:
      - regex 1

    - worker:
      - regex 2
      - regex 3

would create 2 workers. The first would run all tests that match regex 1, and
the second would run all tests that match regex 2 or regex 3. In addition if
you need to mix manual scheduling and the standard scheduling mechanisms you
can accomplish this with the ``concurrency`` field on a worker in the yaml.
For example, building on the previous example::

    - worker:
      - regex 1

    - worker:
      - regex 2
      - regex 3

    - worker:
      - regex 4
      concurrency: 3

In this case the tests that match regex 4 will be run against 3 workers and the
tests will be partitioned across those workers with the normal scheduler. This
includes respecting the other scheduler options, like ``group_regex`` or
``--random``.

There is also an option on ``stestr run``, ``--random`` to randomize the
order of tests as they are passed to the workers. This is useful in certain
use cases, especially when you want to test isolation between test cases.


User Config Files
-----------------

If you prefer to have a different default output or setting for a particular
command stestr enables you to write a user config file to overide the defaults
for some options on some commands. By default stestr will look for this config
file in ``~/.stestr.yaml`` and ``~/.config/stestr.yaml`` in that order. You
can also specify the path to a config file with the ``--user-config``
parameter.

The config file is a yaml file that has a top level key for the command and
then a sub key for each option. For an example, a fully populated config file
that changes the default on all available options in the config file is::

    run:
      concurrency: 42 # This can be any integer value >= 0
      random: True
      no-subunit-trace: True
      color: True
      abbreviate: True
      slowest: True
      suppress-attachments: True
      all-attachments: True
    failing:
      list: True
    last:
      no-subunit-trace: True
      color: True
      suppress-attachments: True
      all-attachments: True
    load:
      force-init: True
      subunit-trace: True
      color: True
      abbreviate: True
      suppress-attachments: True
      all-attachments: True
    history-list:
      show-metadata: True
    history-show:
      no-subunit-trace: True
      color: True
      suppress-attachments: True
      all-attachments: True

If you choose to use a user config file you can specify any subset of the
options and commands you choose.

Automated test isolation bisection
----------------------------------

As mentioned above, its possible to manually analyze test isolation issues by
interrogating the repository for which tests ran on which worker, and then
creating a list file with those tests, re-running only half of them, checking
the error still happens, rinse and repeat.

However that is tedious. stestr can perform this analysis for you::

  $ stestr run --analyze-isolation

will perform that analysis for you. The process is:

1. The last run in the repository is used as a basis for analysing against -
   tests are only cross checked against tests run in the same worker in that
   run. This means that failures accrued from several different runs would not
   be processed with the right basis tests - you should do a full test run to
   seed your repository. This can be local, or just stestr load a full run from
   your Jenkins or other remote run environment.

2. Each test that is currently listed as a failure is run in a test process
   given just that id to run.

3. Tests that fail are excluded from analysis - they are broken on their own.

4. The remaining failures are then individually analysed one by one.

5. For each failing, it gets run in one work along with the first 1/2 of the
   tests that were previously run prior to it.

6. If the test now passes, that set of prior tests are discarded, and the
   other half of the tests is promoted to be the full list. If the test fails
   then other other half of the tests are discarded and the current set
   promoted.

7. Go back to running the failing test along with 1/2 of the current list of
   priors unless the list only has 1 test in it. If the failing test still
   failed with that test, we have found the isolation issue. If it did not
   then either the isolation issue is racy, or it is a 3-or-more test
   isolation issue. Neither of those cases are automated today.

Forcing isolation
-----------------

Sometimes it is useful to force a separate test runner instance for each test
executed. The ``--isolated`` flag will cause stestr to execute a separate
runner per test::

  $ stestr run --isolated

In this mode stestr first determines tests to run (either automatically listed,
using the failing set, or a user supplied load-list), and then spawns one test
runner per test it runs. To avoid cross-test-runner interactions concurrency
is disabled in this mode. ``--analyze-isolation`` supersedes ``--isolated`` if
they are both supplied.

History
-------

stestr keeps a history of all test runs in a local repository. the
``stestr history`` command is used for interacting with those old runs. The
history command has 3 sub-commands, ``list``, ``show``, and ``remove``. The
``list`` sub-command will generate a list of the previous runs in the data
repository and show some basic stats for each run. The ``show`` sub-command is
used to retreive the record of a previous run, it behaves identically to
``stestr last``, except that it takes an optional run id to show any run in the
stestr history. If a run id is not specified it will use the most recent
result. The ``remove`` sub-command will delete a specified run from the data
repository. Additionally, the keyword ``all`` can be used to remove all runs
from the repository. For example::

  $ stestr history remove all

Repositories
------------

stestr uses a data repository to keep track of test previous test runs.

You can also specify an alternative repository with the ``--repo-url``/``-u``
cli flags. The default value is to use the directory: ``$CWD/.stestr``.

.. note:: Make sure you put these flags before the cli subcommand

The stestr repository has a very simple disk structure. It contains the
following files:

* format: This file identifies the precise layout of the repository, in case
  future changes are needed.

* next-stream: This file contains the serial number to be used when adding
  another stream to the repository.

* failing: This file is a stream containing just the known failing tests. It
  is updated whenever a new stream is added to the repository, so that it only
  references known failing tests.

* #N - all the streams inserted in the repository are given a serial number.

* times.dbm: A dbm database (using Python's
  ```dbm.dumb`` <https://docs.python.org/3/library/dbm.html#module-dbm.dumb>`__
  implementation) that stores the record of the last elapsed time for each test
  executed.

* meta.dbm: An dbm file that maps a run id (which will be the integer file
  documented above) to an arbitrary string metadata field describing the run.
  Right now this must be manually specified.
