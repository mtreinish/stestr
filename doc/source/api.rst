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

Commands
--------

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
   api/test_listing_fixture
