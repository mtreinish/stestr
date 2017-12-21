.. _api:

Internal API Reference
======================
This document serves as a reference for the python API used in stestr. It should
serve as a guide for both internal and external use of stestr components via
python. The majority of the contents here are built from internal docstrings
in the actual code.

Repository
----------

.. toctree::
   :maxdepth: 2

   api/repository/abstract
   api/repository/file
   api/repository/memory
   api/repository/sql

Commands
--------

These modules are used for the operation of all the various subcommands in
stestr. As of the 1.0.0 release each of these commands should be considered
a stable interface that can be relied on externally.

Each command module conforms to a basic format that is used by ``stestr.cli``
to load each command. The basic structure for these modules is the following
three functions::

  def get_cli_help():
      """This function returns a string that is used for the subcommand help"""
      help_str = "A descriptive help string about the command"
      return help_str

  def get_cli_opts(parser):
      """This function takes a parser and any subcommand arguments are defined
         here"""
      parser.add_argument(...)

  def run(arguments):
      """This function actually runs the command. It takes in a tuple arguments
         which the first element is the argparse Namespace object with the
         arguments from the parser. The second element is a list of unknown
         arguments from the CLI. The expectation of the run method is that it
         will process the arguments and call another function that does the
         real work. The return value is expected to be an int and is used for
         the exit code (assuming the function doesn't call sys.exit() on it's
         own)"""
      args = arguments[0]
      unknown_args = arguments[1]
      return call_foo()

The command module will not work if all 3 of these function are not defined.
However, to make the commands externally consumable each module also contains
another public function which performs the real work for the command. Each one
of these functions has a defined stable Python API signature with args and
kwargs so that people can easily call the functions from other python programs.
This function is what can be expected to be used outside of stestr as the stable
interface.
All the stable functions can be imported the command module directly::

  from stestr import command

  def my_list():
      command.list_command(...)

.. toctree::
   :maxdepth: 2

   api/commands/__init__
   api/commands/failing
   api/commands/init
   api/commands/last
   api/commands/list
   api/commands/load
   api/commands/run
   api/commands/slowest


Internal APIs
-------------

The modules in this list do not necessarily have any external api contract,
they are intended for internal use inside of stestr. If anything in these
provides a stable contract and is intended for usage outside of stestr it
will be noted in the api doc.

.. toctree::
   :maxdepth: 2

   api/config_file
   api/selection
   api/scheduler
   api/output
   api/test_processor
   api/subunit_trace
