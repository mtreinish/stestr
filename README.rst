Slim/Super Test Repository
==========================

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
