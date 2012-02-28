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
* ``cron_sync``: See `Scheduling sync operations with cron`_ (Not Yet Implemented)


Repository Status Queries
~~~~~~~~~~~~~~~~~~~~~~~~~

* ``list``: Display id and name for repositories
* ``info``: Display details for repositories
* ``status``: Display repository synchronisation status
* ``history``: Display repository synchronisation history
* ``sync_log``: Display most recent synchronisation log
* ``sync_stats``: Display most recent synchronisation statistics


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

The ``--remote-tree`` option accepts remote tree identifiers and allows a
command to run against repositories that were configured from a site
configuration file to sync with a particular remote tree. It may be
supplied multiple times to run a command against mirrors of multiple trees.

The ``--remote-source`` option accepts remote source identifiers and allows a
command to run against repositories that were configured from a site
configuration file to sync with a tree from that remote source. It may be
supplied multiple times to run a command against repositories from multiple
sources.

The ``--remote-server`` option accepts remote server identifiers and allows a
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

.. note::

   ``--site``, ``--remote-tree``, ``--remote-source`` and ``--remote-server``
   are not yet implemented

Scheduling sync operations
--------------------------

Scheduling sync operations with Pulp
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Eventually, PulpDist will use the native Pulp task scheduler for sync
operations. However, this is not yet supported by Pulp for plugin based
repositories (such as those used by PulpDist).


Scheduling sync operations with cron
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note:: This operation is not yet implemented

As Pulp does not currently provide native sync scheduling support for plugin
based repositories), PulpDist offers a simple alternative mechanism based on
cron (or any similar tool that can be used to periodically execute a Python
script).

The relevant command is::

    python -m pulpdist.manage_repos cron_sync

This tool is designed to be run every few minutes (if a previous instance for
the same Pulp host is still running, the new instance will immediately exit).

The command first retrieves the list of repository definitions from the
Pulp server and queries each one for a ``["notes"]["pulpdist"]["sync_hours"]``
setting in the metadata.

If sync operations on the repository are currently enabled, the repository
does not already have a sync operation in progress, the ``sync_hours`` setting
is found and is non-zero, and there is either no last sync attempt
time recorded, or that time is more than ``sync_hours`` in the past, then a
new thread is spawned to request immediate synchronisation of the repository
through the Pulp REST API.

Otherwise, the repository is ignored until the next check for new sync
operations.

As long as any sync operations are still in progress, the client will
periodically query the server for updated information, scheduling sync
operations as appropriate.

As soon as all sync operations are complete (regardless of success or failure),
the client will terminate.

The following options can be set to control the sync operation:

* ``--threads``: maximum number of concurrent sync operations (default: 8)
* ``--query``: time to wait in minutes between server queries (default: 2)
* ``--day``: rsync bandwidth limit to apply during the day (6 am - 6 pm)
* ``--night``: rsync bandwidth limit to apply at night (6 pm - 6 am)

By default, no bandwidth limits are applied.


The repository definition file format
-------------------------------------

The ``init`` and ``validate`` commands provided by ``manage_repos`` both
require a repository definition file. The ``export`` command generates a
respository definition file describing the server contents.

These are JSON files that specify the information needed to create the
repositories on the Pulp server, and appropriately configure the associated
importer plugins.

Currently, only the `raw configuration format`_ is supported. A
higher level `site configuration format`_ is in development.

``init`` and ``validate`` will accept either format (deciding which to use
based on whether the top level JSON value is a sequence or mapping).

``export`` (once implemented) will always emit a site configuration file.


Raw configuration format
~~~~~~~~~~~~~~~~~~~~~~~~

A raw config file consists of a single top-level JSON sequence, containing
`raw tree definitions`_.


Site configuration format
~~~~~~~~~~~~~~~~~~~~~~~~~

.. note:: This configuration format is not yet implemented

Whereas the raw configuration format maps almost directly to Pulp API calls
and plugin configuration settings, the site configuration format revolves
around the idea of sharing common settings across multiple tree definitions.

A site config file consists of a top-level JSON mapping, defining
the following attributes:

* ``LOCAL_TREES``: A sequence of `local tree definitions`_.
* ``REMOTE_TREES``: A sequence of `remote tree definitions`_.
* ``REMOTE_SOURCES``: A sequence of `remote source definitions`_.
* ``REMOTE_SERVERS``: A sequence of `remote server definitions`_.
* ``SITE_SETTINGS``: A sequence of `site definitions`_.
* ``RAW_TREES``: A sequence of `raw tree definitions`_.

The general concept is that:

* each local tree mirrors a particular remote tree
* each remote tree is provided by a particular remote source
* each remote source is provided by a particular remote server
* these settings are combined with the appropriate site settings to create
  raw tree definitions that are uploaded to the server
* details of the original settings are stored in the raw tree metadata,
  allowing them to be exported again if necessary
* additional raw trees can be defined and are passed directly to the Pulp
  server


Local Tree Definitions
^^^^^^^^^^^^^^^^^^^^^^

A local tree is a PulpDist managed mirror of a remote tree.

A local tree definition is a mapping with the following attributes:

* ``repo_id``: locally unique ID (alphanumeric characters and hyphens only)
* ``tree_id``: the ID of the remote tree that this local tree mirrors
* ``name``: human readable name of local tree (default: same as remote tree)
* ``description``: description of local tree (default: same as remote tree)
* ``tree_path``: final path segment for this tree (default: same as remote tree)
* ``enabled``: whether the tree starts with sync enabled (default: false)
* ``dry_run_only``: whether the tree starts in dry run mode (default: false)
* ``excluded_files``: rsync wildcard patterns to ignore when retrieving files
  (optional)
* ``sync_filters``: additional rsync filters applied when retrieving files
  (optional)
* ``notes``: additional notes to store in the Pulp repo metadata (optional)

The ``excluded_files`` and ``sync_filters`` settings are appended to the
default filtering options including in the remote tree definition.

The following additional settings are only valid if the remote tree specifies
the use of either ``versioned`` or ``snapshot`` as the sync algorithm:

* ``delete_old_dirs``: whether local dirs no longer in the remote tree are
  deleted (default: false)
* ``excluded_versions``: additional rsync wildcard patterns to ignore when
  determining which version directories to synchronise (optional)
* ``version_filters``: additional rsync filters applied when determining
  which version directories to synchronise (optional)

The ``excluded_versions`` and ``version_filters`` settings are appended to
the default filtering options including in the remote tree definition.


Remote Tree Definitions
^^^^^^^^^^^^^^^^^^^^^^^

A remote tree is a file tree available for synchronisation via rsync.

A remote tree definition is a mapping with the following attributes:

* ``tree_id``: locally unique ID (alphanumeric characters and hyphens only)
* ``source_id``: the ID of the remote source that publishes this tree
* ``name``: human readable name of tree
* ``description``: description of tree
* ``tree_path``: final path segment for this tree (before the tree contents)
* ``sync_hours``: used for `scheduling sync operations with cron`_.
* ``sync_type``: the tree sync algorithm to use. See below for details.
* ``excluded_files``: rsync wildcard patterns to ignore when retrieving files
  (optional)
* ``sync_filters``: additional rsync filters applied when retrieving files
  (optional)

The currently supported sync algorithms are:

* ``simple``: Settings are derived for a :ref:`simple-tree-sync`
* ``versioned``: Settings are derived for a :ref:`versioned-tree-sync`
* ``snapshot``: Settings are derived for a :ref:`snapshot-tree-sync`

The following additional settings are only valid if the sync algorithm is
either ``versioned`` or ``snapshot``:

* ``version_pattern``: rsync wildcard pattern used to determine which
  directories to synchronise (default: '*')
* ``version_prefix``: alternative mechanism to specify the version pattern
  as ``version_prefix + version_suffix`` (where the latter comes from the
  shared remote tree settings.
* ``excluded_versions``: rsync wildcard patterns to ignore when determining
  which version directories to synchronise (optional)
* ``version_filters``: rsync filters applied when determining which version
  directories to synchronise (optional)


Remote Source Definitions
^^^^^^^^^^^^^^^^^^^^^^^^^

A remote source describes common settings for a group of remote trees.

A remote source definition is a mapping with the following attributes:

* ``source_id``: locally unique ID (alphanumeric characters and hyphens only)
* ``server_id``: the ID of the remote server that publishes these trees
* ``name``: human readable name for this group of remote trees
* ``remote_path``: shared path prefix for these trees on the remote server


Remote Server Definitions
^^^^^^^^^^^^^^^^^^^^^^^^^

A remote server describes the location of an actual rsync server.

A remote server definition is a mapping with the following attributes:

* ``server_id``: locally unique ID (alphanumeric characters and hyphens only)
* ``name``: human readable name for this server
* ``dns``: DNS name used to access this server
* ``old_daemon``: Server runs an old version of rsync (default: False)
* ``rsync_port``: Port rsync daemon is listening on (default: rsync default)


Site Definitions
^^^^^^^^^^^^^^^^

A site definition a mapping with the following attributes:

* ``site_id``: locally unique ID (alphanumeric characters and hyphens only)
* ``name``: human readable name for this site
* ``storage_prefix``: The shared path prefix for the local data storage area
* ``server_prefixes``: mapping from ``server_id`` values to path segments
* ``source_prefixes``: mapping from ``source_id`` values to path segments
* ``version_suffix``: rsync wildcard pattern to append when a remote tree
  definition uses the ``version_prefix`` setting
* ``default_excluded_versions``: rsync wildcard patterns to ignore by default
  when determining which version directories to synchronise (if one of these
  filters matches the wildcard pattern identifying *desired* versions, then
  that exclusion filter will be omitted from the raw tree definition).
* ``default_excluded_files``: rsync wildcard patterns that are always ignored
  when creating a raw tree definition (e.g. to exclude standard locations for
  temporary working files)

The special ``default`` site settings are used if no more specific settings are
provided to override them.

Raw Tree Definitions
^^^^^^^^^^^^^^^^^^^^

Raw tree definitions are a low-level interface that corresponds directly with
the settings accepted by the underyling calls to the Pulp REST API. They allow
direct specification of sync operations at the rsync level without needing to
create single use remote tree, source and server definitions.

A raw tree definition is a mapping with the following attributes:

* ``repo_id``: Locally unique repo ID (alphanumeric characters and hyphens only)
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


Deriving Raw Tree Definitions from Local Tree Definitions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Deriving raw tree definitions from a local tree definitions requires that a
specific site be nominated (e.g. via the ``--site`` flag to the ``init``
command). If no site is nominated, or the site settings have no entry for a
particular value, then the corresponding settings for the ``default`` site
are used instead.

The local path used in the import configuration is calculated as::

   storage_prefix/server_prefix/source_prefix/local_tree_path

Where:

* ``storage_prefix`` is taken directly from the site settings
* ``server_prefix`` is looked up in the server prefixes map. If it is not
  defined for either the specified site or the default site, then the empty
  string is used.
* ``source_prefix`` is looked up in the source prefixes map. If it is not
  defined for either the specified site or the default site, then the empty
  string is used.
* ``local_tree_path`` is the ``tree_path`` setting for the local tree, if
  it is defined, otherwise it uses the setting for the remote tree.

The remote path used to retrieve a tree is calculated as::

   rsync://server_dns/source_remote_path/remote_tree_path

These values are all taken directly from the appropriate remote server, remote
source and remote tree settings, respectively.



Example site definition file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following file is an example site definition provided in the PulpDist
source tree for demonstration purposes:

.. literalinclude:: ../misc/example_site.json
   :language: js


Example raw repository definition file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following file is a set of example repositories defined in the PulpDist
source tree for demonstration purposes:

.. literalinclude:: ../misc/example_repos.json
   :language: js


PulpDist metadata in Pulp
-------------------------

.. note:: this metadata storage scheme is not yet implemented

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
  * ``tree_id``: The remote tree mirrored by this repo
  * ``source_id``: The remote source for this tree
  * ``server_id``: The remote server for this tree
