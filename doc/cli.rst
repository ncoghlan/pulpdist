.. _pulpdist-cli:

PulpDist Repository Management Client
=====================================

The upstream Pulp project does not currently provide a management client for
repositories that use the new plugin model. Accordingly, PulpDist comes with
a command line interface for working with these repositories.


Invoking the Client
-------------------

At this stage, there is no separately installed executable script to manage
repositories. Instead, a feature of the CPython interpreter is used to invoke
the appropriate module as a command line script::

   $ python -m pulpdist.manage_repos --help

Before using the command line client to manage a Pulp server, it is necessary
to create the login credentials for the Pulp server with the upstream
``pulp-admin`` client (entering the appropriate password when prompted)::

   $ pulp-admin --host <HOST> auth login --username <USER>


Available Commands
------------------

* ``list``: Display id and name for repositories
* ``info``: Display repository details
* ``status``: Display repository synchronisation status
* ``sync``: Request immediate synchronisation of repositories
* ``init``: Create or update repositories on the server
* ``delete``: Remove repositories from the server
* ``validate``: Check the validity of a repository definition file


The repository definition file format
-------------------------------------

All of the management commands supported by ``manage_repos`` either accept or
require a repository definition file.

These are JSON files that identify exactly which repositories on the server
should be affected by the command. For most commands, the only requirements are
that the file be valid JSON consisting of:

* a single top-level list
* each entry in the list is a mapping with at least a ``repo_id`` attribute

For commands where the repository definition file is optional, omitting it
means "every repository currently defined on the server".

For the ``init`` command (which actually creates and updates repositories on
the server), additional information is needed in the repository definition
file for each repo entry, as per the Pulp `Create Repository`_ and
`Add Importer`_ REST API calls.

.. _Create Repository: https://fedorahosted.org/pulp/wiki/UGREST-v2-Repositories#CreateaRepository
.. _Add Importer: https://fedorahosted.org/pulp/wiki/UGREST-v2-Repositories#AssociateanImportertoaRepository


Example repository definition file
----------------------------------

The following file is a set of example repositories defined in the PulpDist
source tree for demonstration purposes:

.. literalinclude:: ../misc/example_repos.json
   :language: js
