Development guidelines for stestr
=================================

Coding style
------------

PEP-8 is used for changes. We enforce running flake8 prior to landing any
commits.

Testing and QA
--------------

For stestr please add tests where possible. There is no requirement
for one test per change (because somethings are much harder to automatically
test than the benfit from such tests). But, if unit testing is reasonable it
will be expected to be present before it can merge.

Running the tests
-----------------

Generally just ``tox`` is all that is needed to run all the tests. However
if dropping into pdb, it is currently more convenient to use
``python -m testtools.run testrepository.tests.test_suite``.


Releasing
---------

Add release notes using reno prior to pushing the release to pypi. Versioning
is handled automatically by pbr, just make sure the tag is a valid version
number. The repo uses semver to dictate version number increments.

Internal Architecture
=====================

This section is an attempt to explain at a high level how stestr is constructed.
It'll likely go stale quickly as the code changes, but hopefully it'll be a
useful starting point for new developers to understand how the stestr is built.
Full API documentation can be found at :ref:`api`. It's also worth noting that
any explanation of workflow or internal operation is not an actual call path,
but instead a high level explanation of how the components operate.

Basic Structure
---------------

At a high level there are a couple different major components to stestr: the
repository, and the cli layer.

The repository is how stestr stores all results from test runs and the source
of any data needed by any stestr operations that require past runs. There are
actually multiple repository types which are different implementations of an
abstract API. Right now there is only one complete implementation, the file
repository type, which is useful in practice but that may not be the case in
the future.

The CLI layer is where the different stestr commands are defined and provides
the command line interface for performing the different stestr operations.

CLI Layer
---------
The CLI layer is built using modular subcommands in argparse. The stestr.cli
module defines a basic interface using argparse and then loops over a list of
command modules in stestr.commands. Each subcommand has its own module in
stestr.commands and has 3 required functions to work properly:

 #. set_cli_opts(parser)
 #. get_cli_help()
 #. run(arguments)

set_cli_opts(parser)
''''''''''''''''''''

This function is used to define subcommand arguments. It has a single argparse
parser object passed into it. The intent of this function is to have any command
specific arguments defined on the provided parser object by calling
`parser.add_argument()`_ for each argument.

.. _parser.add_argument(): https://docs.python.org/2/library/argparse.html#the-add-argument-method

get_cli_help()
''''''''''''''
The intent of this function is to return an command specific help information.
It is expected to return a string that will be used when the subcommand is
defined in argparse and will be displayed before the arguments when --help is
used on the subcommand.

run(arguments)
''''''''''''''
This is where the real work for the command is performed. This is the function
that is called when the command is executed. This function is called being
wrapped by sys.exit() so an integer return is expected that will be used
for the command's return code.

.. todo::
  Define an API for the arguments. Right now it's a tuple with a
  argparse.Namespace object and a list, but this isn't set in stone.


Operation of Running Tests
--------------------------

When running tests stestr first does unittest discovery to find a complete list
of tests present. This list is then filtered by any user selected provided
selection mechanisms. Once there is a list of tests to be run this gets passed
to the scheduler/partitioner. This takes the list of tests and splits it into
N groups where N is the concurrency that stestr will use to run tests. If there
is timing data available in the repository from previous runs this is used by
the scheduler to try and ensure that the workers are balanced. Each group of
tests is then used to launch a subunit.run worker proccess that will execute the
list of tests and emit a subunit stream. These streams are combined in real
time and stored in the repository at the end of the run. The combined stream is
also used for the CLI output.
