.. _pulp-plugins:

PulpDist Custom Plugins
=======================

The custom Pulp plugins for PulpDist use ``rsync`` under the hood to perform
efficient updates over the network. They currently use the ``rsync`` CLI
directly, but may eventually move to a more programmatic API based on
``librsync``.


Sync Operation Results
----------------------

Each of the PulpDist sync plugins may report the following results:

* ``SYNC_UP_TO_DATE``: the local copy was up to date, no changes were made.
* ``SYNC_COMPLETED``: upstream changes were found and applied locally
* ``SYNC_PARTIAL``: upstream changes were found, but the attempt to apply them
  locally failed to incorporate some changes (see log output for details)
* ``SYNC_FAILED``: sync completely failed (e.g. upstream could not be reached)
* ``SYNC_DISABLED``: the plugin has been set to ignore sync requests

These statuses may also be reported with ``_DRY_RUN`` appended to indicate
that a sync operation was executed with rsync configured to avoid actually
transferring any files (some temporary local copies of small metadata files
may still be made in order to determine the details of the dry run operation).


.. _simple-tree-sync:

Simple Tree Sync
----------------

A simple tree sync is a convenient way to define and schedule an rsync task.
Configuration options for this plugin are:

* ``tree_name``: A short text name for the tree
* ``remote_server``: The host name or IPv4 address of the source rsync server
* ``remote_path``: The path to read from on the remote server
* ``local_path``: The local destination path for the received tree
* ``exclude_from_sync``: A list of rsync ``--exclude`` patterns applied to the
  tree synchronisation operation. Defaults to no exclusions.
* ``sync_filters``: A list of rsync ``--filter`` patterns applied to the
  tree synchronisation operation. Defaults to no filtering.
* ``bandwidth_limit``: If provided and not zero, passed to rsync as
  ``--bwlimit`` to limit the amount of bandwidth used by the operation.
* ``old_remote_daemon``:  If provided and true, passes ``--no-implied-dirs`` to
  rsync to run it in a mode compatible with older versions of the rsync daemon.
* ``rsync_port``: If provided and not zero, passed to rsync as ``--port`` to
  allow connections to a remote daemon that isn't running on the default port.
* ``enabled``: If provided and true, actually performs a sync operation when
  invoked by Pulp. Defaults to ignoring sync requests.
* ``dry_run_only``: If provided and true, passes ``-n`` to rsync to run it in
  "dry run" mode (i.e. no actual file transfers will take place).

Adding files named ``PROTECTED`` to directories at downstream sites will
keep the plugin from overwriting (or otherwise altering) them.


.. _versioned-tree-sync:

Versioned Tree Sync
-------------------

A versioned tree sync works like a series of simple tree syncs. It is
intended for directories containing multiple versions of a single tree,
where each tree may change over time. The trees are synchronised in separate
operations, but the sync process attempts to create hard links between
the trees whenever possible.

In addition to all of the simple tree sync configuration options, the
versioned tree sync has the following additional options that are used to
build the list of individual subtrees to be synchronised:

* ``listing_pattern``: An rsync ``--include`` pattern identifying the subtrees
  to synchronise. Defaults to all subdirectories of ``remote_path``.
* ``exclude_from_listing``: A list of rsync ``--exclude`` patterns applied to
  the subtree listing operation. Defaults to no filtering.
* ``listing_filters``: A list of rsync ``--filter`` patterns applied to the
  subtree listing operation. Defaults to no filtering.
* ``delete_old_dirs``: If provided and true, removes local subdirectories that
  are no longer present on the source server. By default, local subdirectories
  are retained until explicitly deleted by a system administrator. Adding a
  ``PROTECTED`` file will also ensure a directory is not deleted automatically.

  To avoid data loss due to network and remote storage glitches, the plugin
  treats the case where absolutely no relevant remote directories are found
  as an error and never deletes local directories in that situation.
  Similarly, if the overall job will be reported as ``SYNC_FAILED``
  or ``SYNC_PARTIAL``, then no local directories will be removed.

The versioned tree sync also reproduces locally any upstream symlinks that
match the listing pattern and point to destinations that exist on the local
server after the sync operation is otherwise complete.

.. _snapshot-tree-sync:

Snapshot Tree Sync
------------------

A snapshot tree sync works like a versioned tree sync, but versions are
never updated after their initial release. "STATUS" marker files in the root
directory of each tree are used to indicate when a tree is completed. Each
tree is synchronised only if the remote tree includes a STATUS file
containing the text ``FINISHED``, and there is no existing local tree that
contains such a file.

The big advantage of snapshot tree syncs is that once a tree has been
marked as complete locally, it never needs to be checked against the
upstream site again.

In addition to all of the versioned tree sync configuration options, the
snapshot tree sync has the following additional options that allow special
treatment for the most recent snapshot (as determined by the timestamps in
the remote directory listing):

* ``latest_link_name``: If provided and not ``None``, a local symbolic link
  is created with this name that points to the most recent snapshot after
  each sync operation. By default, no symbolic link is created.
* ``sync_latest_only``: If provided and true, only the most recent remote
  snapshot will be mirrored locally. By default, all remote snapshots are
  mirrored.

The snapshot tree sync also modifies the behaviour of the ``delete_old_dirs``
setting: the most recently synchronised snapshot will *never* be deleted
automatically, even after it has been deleted remotely. This is useful
when mirroring snapshots generated by an automatic build process that
only retains a limited number of build attempts, regardless of whether or
not the build succeeded. Retaining the most recent snapshot ensures that
there will always be a version of the tree available for local use,
the "latest snapshot" symlink (if defined) will remain valid, and future
sync operations will have a base to use for hardlinking previously
synchronised files.

Snapshot Delta Sync
-------------------

.. note: The plugins for delta sync support are not yet implemented.

Delta syncs actually require an upstream Pulp server (rather than just
an rsync daemon) and use a chain of 3 custom Pulp plugins.

At the upstream site, rsync is run in batch mode to generate delta files
to update from the previous version of the tree to the latest snapshot.

These delta files are then published for retrieval by the downstream servers.

The downstream servers first check if a delta file is available that
is applicable to the most recent version of the tree they have completed
locally. If it exists, they download and apply it. Otherwise, they fall
back on doing a full synchronisation via rsync (i.e. the same process as an
ordinary snapshot tree sync)
