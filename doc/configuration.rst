.. _pulpdist-site-config:

PulpDist Site Configuration
===========================

The PulpDist site configuration file is used to describe the full set of
mirroring tasks to be carried out at a site. It is designed to allow data
source definitions to be shared amongst multiple sites, and even to define
the jobs for multiple sites within a single file.


.. _site-config-def:

Site Configuration Components
-----------------------------

A site config file consists of a top-level JSON mapping, defining
the following attributes:

* ``LOCAL_MIRRORS``: A sequence of `local mirror definitions`_.
* ``REMOTE_TREES``: A sequence of `remote tree definitions`_.
* ``REMOTE_SOURCES``: A sequence of `remote source definitions`_.
* ``REMOTE_SERVERS``: A sequence of `remote server definitions`_.
* ``SITE_SETTINGS``: A sequence of `site definitions`_.
* ``RAW_REPOS``: A sequence of `raw repo definitions`_.

The general concept is that:

* each local tree mirrors a particular remote tree
* each remote tree is provided by a particular remote source
* each remote source is provided by a particular remote server
* these settings are combined with the appropriate site settings to create
  raw repo definitions that are uploaded to the server
* details of the original settings are stored in the raw repo metadata,
  allowing them to be exported again if necessary
* additional raw repos can be defined and are passed directly to the Pulp
  server

The current format doesn't allow for the definition of alternative sources for
a given tree, but this capability may be added in the future.


.. _local-mirror-def:

Local Mirror Definitions
^^^^^^^^^^^^^^^^^^^^^^^^

A local mirror is a PulpDist managed mirror (possibly filtered) of a remote
tree.

A local mirror definition is a mapping with the following attributes:

* ``mirror_id``: locally unique ID (alphanumeric characters and hyphens only)
* ``tree_id``: the ID of the remote tree that this local tree mirrors
* ``site_id``: the ID of the site settings used for this tree (default: ``"default"``)
* ``name``: human readable name of local tree (default: same as remote tree)
* ``description``: description of local tree (default: same as remote tree)
* ``mirror_path``: final path segment for this tree (default: same as tree_path)
* ``enabled``: whether the tree starts with sync enabled (default: false)
* ``dry_run_only``: whether the tree starts in dry run mode (default: false)
* ``exclude_from_sync``: rsync wildcard patterns to ignore when retrieving
  files (optional)
* ``sync_filters``: additional rsync filters applied when retrieving files
  (optional)
* ``notes``: additional notes to store in the Pulp repo metadata (optional)

The ``exclude_from_sync`` and ``sync_filters`` settings are appended to the
default filtering options including in the remote tree definition.

The following additional settings are only valid if the remote tree specifies
the use of either ``versioned`` or ``snapshot`` as the sync algorithm:

* ``delete_old_dirs``: whether local dirs no longer in the remote tree are
  deleted (default: false)
* ``exclude_from_listing``: additional rsync wildcard patterns to ignore when
  determining which version directories to synchronise (optional)
* ``listing_filters``: additional rsync filters applied when determining
  which version directories to synchronise (optional)

The ``exclude_from_listing`` and ``listing_filters`` settings are appended to
the default filtering options including in the remote tree definition.

The following additional settings is only valid if the sync algorithm is set to
``snapshot``:

* ``sync_latest_only``: If provided and true, only the most recent remote
  snapshot will be mirrored locally. By default, all remote snapshots are
  mirrored.


.. _remote-tree-def:

Remote Tree Definitions
^^^^^^^^^^^^^^^^^^^^^^^

A remote tree is a file tree available for synchronisation via rsync.

A remote tree definition is a mapping with the following attributes:

* ``tree_id``: locally unique ID (alphanumeric characters and hyphens only)
* ``source_id``: the ID of the remote source that publishes this tree
* ``name``: human readable name of tree
* ``description``: description of tree
* ``tree_path``: final path segment for this tree (before the tree contents)
* ``sync_hours``: used for :ref:`cron-sync`.
* ``sync_type``: the tree sync algorithm to use. See below for details.
* ``exclude_from_sync``: rsync wildcard patterns to ignore when retrieving
  files (optional)
* ``sync_filters``: additional rsync filters applied when retrieving files
  (optional)

The currently supported sync algorithms are:

* ``simple``: Settings are derived for a :ref:`simple-tree-sync`
* ``versioned``: Settings are derived for a :ref:`versioned-tree-sync`
* ``snapshot``: Settings are derived for a :ref:`snapshot-tree-sync`

The following additional settings are only valid if the sync algorithm is
either ``versioned`` or ``snapshot``:

* ``listing_pattern``: rsync wildcard pattern used to determine which
  directories to synchronise (default: '*')
* ``listing_prefix``: alternative mechanism to specify the listing pattern
  as ``listing_prefix + listing_suffix`` (where the latter comes from the
  remote source settings).
* ``exclude_from_listing``: rsync wildcard patterns to ignore when determining
  which directories to synchronise (optional)
* ``listing_filters``: rsync filters applied when determining which directories
  to synchronise (optional)

The following additional setting is only valid if the sync algorithm is set to
``snapshot``:

* ``latest_link``: the filename used for a symlink that refers to the most
  recently synchronised snapshot directory. If omitted, indicates that no
  such symlink should be created.


.. _remote-source-def:

Remote Source Definitions
^^^^^^^^^^^^^^^^^^^^^^^^^

A remote source describes common settings for a group of remote trees.

A remote source definition is a mapping with the following attributes:

* ``source_id``: locally unique ID (alphanumeric characters and hyphens only)
* ``server_id``: the ID of the remote server that publishes these trees
* ``name``: human readable name for this group of remote trees
* ``remote_path``: shared path prefix for these trees on the remote server
* ``listing_suffix``: rsync wildcard pattern to append when a remote tree
  definition uses the ``listing_prefix`` setting


.. _remote-server-def:

Remote Server Definitions
^^^^^^^^^^^^^^^^^^^^^^^^^

A remote server describes the location of an actual rsync server.

A remote server definition is a mapping with the following attributes:

* ``server_id``: locally unique ID (alphanumeric characters and hyphens only)
* ``name``: human readable name for this server
* ``dns``: DNS name used to access this server
* ``old_daemon``: Server runs an old version of rsync (default: False)
* ``rsync_port``: Port rsync daemon is listening on (default: rsync default)


.. _site-def:

Site Definitions
^^^^^^^^^^^^^^^^

A site definition is a mapping with the following attributes:

* ``site_id``: locally unique ID (alphanumeric characters and hyphens only)
* ``name``: human readable name for this site
* ``storage_prefix``: The shared path prefix for the local data storage area
* ``server_prefixes``: mapping from ``server_id`` values to path segments
* ``source_prefixes``: mapping from ``source_id`` values to path segments
* ``exclude_from_listing``: rsync wildcard patterns to ignore by default
  when determining which version directories to synchronise (if one of these
  filters matches the wildcard pattern identifying *desired* versions, then
  that exclusion filter will be omitted from the raw repo definition).
* ``exclude_from_sync``: rsync wildcard patterns that are always ignored
  when creating a raw repo definition (e.g. to exclude standard locations for
  temporary working files)


.. _raw-repo-def:

Raw Repo Definitions
^^^^^^^^^^^^^^^^^^^^

Raw repo definitions are a low-level interface that corresponds directly with
the settings accepted by the underyling calls to the Pulp REST API. They allow
direct specification of sync operations at the rsync level without needing to
create single use remote tree, source and server definitions.

A raw repo definition is a mapping with the following attributes:

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


.. _deriving-repo-defs:

Deriving Raw Repo Definitions from Local Mirror Definitions
-----------------------------------------------------------

Deriving raw repo definitions from local mirror definitions requires that a
specific site be nominated. If no site is nominated, or the site settings
have no entry for a particular value, then the corresponding settings for
the ``default`` site are used instead.

The local path used in the import configuration is calculated as::

   storage_prefix/server_prefix/source_prefix/local_tree_path

Where:

* ``storage_prefix`` is taken directly from the site settings
* ``server_prefix`` is looked up in the server prefixes map. If it is not
  defined for either the specified site or the default site, then the empty
  string is used (and the now redundant extra path separator is omitted).
* ``source_prefix`` is looked up in the source prefixes map. If it is not
  defined for either the specified site or the default site, then the empty
  string is used (and the now redundant extra path separator is omitted).
* ``local_tree_path`` is the ``tree_path`` setting for the local tree, if
  it is defined, otherwise it uses the setting for the remote tree.

The remote path used to retrieve a tree is calculated as::

   rsync://server_dns/source_remote_path/remote_tree_path

These values are all taken directly from the appropriate remote server, remote
source and remote tree settings, respectively.

The filtering options for the sync process (and, if applicable, the listing
process) are determined by inspecting the settings for the local mirror, the
remote tree, the local site and the default site. All filtering options given
in any of those applications are applied to the underlying rsync command. (The
one exception is that any listing exclusion settings that would exclude
directories matching the listing pattern for a particular tree are omitted
from the remote listing command for that tree).

For the ``sync_filters`` and ``listing_filters`` properties, order is
preserved and the filters for the local mirror are added to the
command line before those for the remote tree.

For the ``exclude_from_sync`` and ``exclude_from_listing`` options, order
is not preserved. The settings for the local mirror, remote tree, specific
site (if any) and default site are merged into a single list in sorted
order with any duplicates remove.

Other settings are derived as detailed in the descriptions of the individual
setting.