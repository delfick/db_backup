Database Backup/Restore
=======================

This holds the necessary code to use existing database dump tools with gpg to
create a full backup of a disk in an encrypted format that can sit on disk more
safely than just a text dump of that database.

This library was originally created for
`RatticWeb <https://github.com/tildaslash/RatticWeb>`_ which made the decision
to not handle encryption within the application itself (encryption is difficult).

Installation
------------

Use pip!:

.. code-block::

    pip install db_backup

Or if you're developing it:

.. code-block::

    pip install -e .
    pip install -e ".[tests]"

Tests
-----

Run the helpful script:

.. code-block::

    ./test.sh

Or if you're outside a virtualenv and want to test with old pythons as well:

.. code-block::

    tox

