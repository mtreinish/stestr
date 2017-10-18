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

Each command module conforms to a basic format that is based on the
`cliff`_ framework. The basic structure for these modules is the
following three functions in each class::

  def get_description():
      """This function returns a string that is used for the subcommand help"""
      help_str = "A descriptive help string about the command"
      return help_str

  def get_parser(prog_name):
      """This function takes a parser and any subcommand arguments are defined
         here"""
      parser.add_argument(...)

  def take_action(parsed_args):
      """This is where the real work for the command is performed. This is the function
         that is called when the command is executed. This function is called being
         wrapped by sys.exit() so an integer return is expected that will be used
         for the command's return code. The arguments input parsed_args is the
         argparse.Namespace object from the parsed CLI options."""
      return call_foo(...)

.. _cliff: https://docs.openstack.org/cliff/latest/reference/index.html

The command class will not work if all 3 of these function are not defined.
However, to make the commands externally consumable each module also contains
another public function which performs the real work for the command. Each one
of these functions has a defined stable Python API signature with args and
kwargs so that people can easily call the functions from other python programs.
This function is what can be expected to be used outside of stestr as the stable
interface.
All the stable functions can be imported the the command module directly::

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
