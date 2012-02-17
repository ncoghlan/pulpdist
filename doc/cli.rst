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

Like ``pulp-admin`` the PulpDist repo management client defaults to using the
fully qualified domain name of the current host as the target server. This can
be overridden by passing a different hostname via the ``--host`` option.

Synchronisation Management Commands
-----------------------------------

* ``sync``: Request immediate synchronisation of repositories
* ``enable``: Configure repositories to respond to sync requests
* ``disable``: Configure repositories to ignore sync requests
* ``cron_sync``: Helper to schedule sync operations via a cron job (Not Yet Implemented)


Repository Status Queries
-------------------------

* ``list``: Display id and name for repositories
* ``info``: Display repository details
* ``status``: Display repository synchronisation status
* ``history``: Display repository synchronisation history
* ``sync_log``: Display most recent synchronisation log
* ``sync_stats``: Display most recent synchronisation statistics


Repository Management Commands
------------------------------

* ``init``: Create or update repositories on the server
* ``delete``: Remove repositories from the server
* ``validate``: Check the validity of a repository definition file
* ``export``: Create a repository definition file from an existing repository
  (Not Yet Implemented)


Limiting a command to specific repositories
-------------------------------------------

The ``--repo`` option accepts repository identifiers and limits a command
to affect only the named repositories. It may be supplied multiple times to
run a command against multiple repositories.

If no specific repositories are identified, most commands default to affecting
every repository defined on the server, or, if the command accepts a
configuration file, every repository named in the file.


The repository definition file format
-------------------------------------

The ``init`` and ``validate`` commands provided by ``manage_repos`` both
require a repository definition file.

These are JSON files that specify the information needed to create the
repository on the Pulp server, and appropriately configure the PulpDist
importer plugin.

Each config file is expected to contain a top-level JSON list, containing
mappings with the following attributes:

* ``repo_id``: An identifier for the repository (alphanumeric and hyphens only)
* ``display_name``: Human readable short name for the repository
* ``description``: Longer description of the repository contents
* ``notes``: Arbitrary notes about the repository as a JSON mapping
* ``importer_type_id``: Importer plugin type identifier. See below.
* ``importer_config``: JSON mapping with plugin configuration data. See below.

The plugin names in the list below are the exact names that should be used in
the ``importer_type_id`` field for the PulpDist plugins, while the links go
to the descriptions of the individual plugins. The options described in those
sections are the values that need to be provided in the ``importer_config``
mapping.

* ``simple_tree``: :ref:`simple-tree-sync`
* ``versioned_tree``: :ref:`versioned-tree-sync`
* ``snapshot_tree``: :ref:`snapshot-tree-sync`


For further information, refer to the documentation for the Pulp
`Create Repository`_ and `Add Importer`_ REST API calls.

.. _Create Repository: https://fedorahosted.org/pulp/wiki/UGREST-v2-Repositories#CreateaRepository
.. _Add Importer: https://fedorahosted.org/pulp/wiki/UGREST-v2-Repositories#AssociateanImportertoaRepository


Example repository definition file
----------------------------------

The following file is a set of example repositories defined in the PulpDist
source tree for demonstration purposes:

.. literalinclude:: ../misc/example_repos.json
   :language: js
