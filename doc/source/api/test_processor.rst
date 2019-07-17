.. _api_test_processor:

Test Processor Module
=====================

This module contains the definition of the ``TestProcessorFixture`` fixture
class. This fixture is used for handling the actual spawning of worker
processes for running tests, or listing tests. It is constructed as a
`fixture`_ to handle the lifecycle of the test id list files which are used to
pass test ids to the workers processes running the tests.

.. _fixture: https://pypi.python.org/pypi/fixtures

In the normal workflow a ``TestProcessorFixture`` get's returned by the
:ref:`api_config_file`'s ``get_run_command()`` function. The config file parses
the config file and the cli options to create a ``TestProcessorFixture`` with
the correct options. This Fixture then gets returned to the CLI commands to
enable them to run the commands.

The ``TestProcessorFixture`` class is written to be fairly generic in the
command it's executing. This is an artifact of being forked from testrepository
where the test command is defined in the configuration file. In stestr the
command is hard coded ``stestr.config_file`` module so this extra flexibility
isn't really needed.

API Reference
-------------

.. automodule:: stestr.test_processor
   :members:
