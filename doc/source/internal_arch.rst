Internal Architecture
=====================

This document is an attempt to explain at a high level how stestr is
constructed. It'll likely go stale quickly as the code changes, but hopefully
it'll be a useful starting point for new developers to understand how the
stestr is built. Full API documentation can be found at :ref:`api`. It's also
worth noting that any explanation of workflow or internal operation is not
necessarily an exact call path, but instead just a high level explanation of
how the components operate.

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
defined in argparse and will be displayed before the arguments when ``--help``
is used on the subcommand.

run(arguments)
''''''''''''''
This is where the real work for the command is performed. This is the function
that is called when the command is executed. This function is called being
wrapped by sys.exit() so an integer return is expected that will be used
for the command's return code. The arguments input arg is a tuple, the first
element is the argparse.Namespace object from the parsed CLI options and the
second element is a list of unknown arguments from the CLI. The expectation
is that this function will call a separate function with a real python API
that does all the real work. (which is the public python interface for the
command)


Operations for Running Tests
----------------------------

The basic flow when stestr run is called at a high level is fairly straight
forward. In the default case when run is called the first operation performed
is unittest discovery (via ``subunit.run --discover``) which is used to get a
complete list of tests present. This list is then filtered by any user provided
selection mechanisms. (for example a cli regex filter) This is used to select
which tests the user actually intends to run. For more details on test
selection see: :ref:`api_selection` which defines the functions which are used
to actually perform the filtering.

Once there is complete list of tests that will be run the list gets passed
to the scheduler/partitioner. The scheduler takes the list of tests and splits
it into N groups where N is the concurrency that stestr will use to run tests.
If there is any timing data available in the repository from previous runs this
is used by the scheduler to try balancing the test load between the workers. For
the full details on how the partitioning is performed see: :ref:`api_scheduler`.

With the tests split into multiple groups for each worker process we're
ready to start executing the tests. Each group of tests is used to launch a
subunit.run worker subprocess. As the name implies this is a test runner that
emits a subunit stream to stdout. These stdout streams are combined in real
time and stored in the repository at the end of the run (using the load
command). The combined stream is also used for the CLI output either in a
summary view or with a real time subunit output (which is enabled with the
``--subunit`` argument)
