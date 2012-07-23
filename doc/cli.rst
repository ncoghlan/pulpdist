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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* ``sync``: Request immediate synchronisation of repositories
* ``enable``: Configure repositories to respond to sync requests
* ``disable``: Configure repositories to ignore sync requests
* ``cron_sync``: See `Scheduling sync operations with cron`_


Repository Status Queries
~~~~~~~~~~~~~~~~~~~~~~~~~

* ``list``: Display id and name for repositories
* ``info``: Display details for repositories
* ``status``: Display repository synchronisation status
* ``history``: Display repository synchronisation history
* ``log``: Display most recent synchronisation log
* ``stats``: Display most recent synchronisation statistics


Repository Management Commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* ``init``: Create or update repositories on the server
* ``delete``: Remove repositories from the server
* ``validate``: Check the validity of a repository definition file
* ``export``: Create a site definition file from an existing repository
  (Not Yet Implemented)


Limiting commands to selected repositories
------------------------------------------

The ``--repo`` option accepts repository identifiers and allows a command
to run against the named repository. It may be supplied multiple times to
run a command against multiple repositories.

The ``--mirror`` option accepts local mirror identifiers and allows a command
to run against the named local mirror. It may be supplied multiple times to
run a command against multiple repositories.

The ``--tree`` option accepts remote tree identifiers and allows a
command to run against repositories that were configured from a site
configuration file to sync with a particular remote tree. It may be
supplied multiple times to run a command against mirrors of multiple trees.

The ``--source`` option accepts remote source identifiers and allows a
command to run against repositories that were configured from a site
configuration file to sync with a tree from that remote source. It may be
supplied multiple times to run a command against repositories from multiple
sources.

The ``--server`` option accepts remote server identifiers and allows a
command to run against repositories that were configured from a site
configuration file to sync with a tree from that remote server. It may be
supplied multiple times to run a command against repositories from multiple
servers.

The ``--site`` option accepts site identifiers and allows a command to run
against repositories that were configured from a site configuration file
based on the specified site settings. It may be supplied multiple times to
run a command against multiple local "sites". This option is only useful if
repositories are configured against more than one site on the specified Pulp
server.

If no specific repositories are identified, most commands default to affecting
every repository defined on the server, or, if the command accepts a
configuration file, every repository named in the file.

By default, the command line client uses the metadata stored on the server to
identify the available repositories. If this metadata is incomplete or invalid,
the ``--ignoremeta`` option can be passed before the command to be executed. In
this mode, the Pulp server will be treated as containing only raw repo
definitions, allowing listing and manipulation of repos that would otherwise be
ignored (due to the fact they aren't recorded in the stored metadata).


Scheduling sync operations
--------------------------

Scheduling sync operations with Pulp
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Eventually, PulpDist will use the native Pulp task scheduler for sync
operations. However, this is not yet supported by Pulp for plugin based
repositories (such as those used by PulpDist).

.. _cron-sync:

Scheduling sync operations with cron
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As the versions of Pulp currently supported by PulpDist do not provide native
sync scheduling support for plugin based repositories), PulpDist offers a
simple alternative mechanism based on cron (or any similar tool that can be
used to periodically execute a Python script).

The relevant command is::

    python -m pulpdist.manage_repos cron_sync

This tool is designed to be run once per hour (if a previous instance for
the same Pulp host is still running, the new instance will immediately exit).
For more immediate synchronisation, the ``sync`` command should be invoked
directly.

The command first retrieves the list of repository definitions from the
Pulp server and queries each one for a ``["notes"]["pulpdist"]["sync_hours"]``
setting in the metadata.

If sync operations on the repository are currently enabled, the repository
does not already have a sync operation in progress, the ``sync_hours`` setting
is found and is non-zero,and the current time (in hours) relative to midnight
is a multiple of the ``sync_hours`` setting, then a new thread is spawned to
request immediate synchronisation of the repository through the Pulp REST API.

Otherwise, the repository is ignored until the next check for new sync
operations.

As long as any sync operations are still in progress, the client will
periodically query the server for updated information, scheduling sync
operations as appropriate.

As soon as all sync operations are complete (regardless of success or failure),
the client will terminate.

The following options can be set to control the sync operation:

* ``--threads``: maximum number of concurrent sync operations (default: 4)
* ``--day``: rsync bandwidth limit to apply during the day (6 am - 6 pm)
* ``--night``: rsync bandwidth limit to apply at night (6 pm - 6 am)

By default, no bandwidth limits are applied.

.. note:: Support for bandwidth limiting is not yet implemented


The repository definition file format
-------------------------------------

The ``init`` and ``validate`` commands provided by ``manage_repos`` both
require a repository definition file. The ``export`` command generates a
respository definition file describing the server contents.

These are JSON files that specify the information needed to create the
repositories on the Pulp server, and appropriately configure the associated
importer plugins. See :ref:`pulpdist-site-config` for more details.


PulpDist metadata in Pulp
-------------------------

When PulpDist repositories are initialised from a site configuration file,
a ``pulpdist-meta`` repo is automatically created to record the full contents
of the original site configuration. This information is stored in the "notes"
field for that repository.

Additional information is also recorded in the ``notes`` field of each created
Pulp repo to support some features of the PulpDist command line client. This
additional metadata is stored in the format:

* ``pulpdist``: Top-level mapping entry to identify pulpdist related metadata

  * ``sync_hours``: The remote tree ``sync_hours`` setting (if any)
  * ``site_id``: The site settings used to configure this repo
  * ``mirror_id``: The local mirror name for this repo
  * ``tree_id``: The remote tree mirrored by this repo
  * ``source_id``: The remote source for this tree
  * ``server_id``: The remote server for this tree

The ``repo_id`` of the associated Pulp repository is built from the
``mirror_id`` and ``site_id`` of the local mirror definition.
