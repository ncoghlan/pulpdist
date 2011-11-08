.. _pulp-plugins:

PulpDist Custom Plugins
=======================

The custom Pulp plugins for PulpDist use ``rsync`` under the hood to perform
efficient updates over the network. They currently use the ``rsync`` CLI
directly, but may eventually move to a more programmatic API based on
``librsync``.


Simple Tree Sync
----------------

A simple tree sync is essentially just a scheduled rsync task. Configuration
options allow specification of such details as:

  * identification of the upstream rsync server
  * excluding certain directories from the transfer
  * addition of arbitrary rsync filtering options
  * storage of the downloaded tree at a specific path

Adding files names "PROTECTED" to directories at downstream sites will
keep the plugin from overwriting (or otherwise altering) them.


Versioned Tree Sync
-------------------

A versioned tree sync works like a series of simple tree syncs. It is
intended for directories containing multiple versions of single tree,
where each tree may change over time. The trees are synchronised in separate
operations, but the sync process attempts to create hard links between
the trees whenever possible.


Snapshot Tree Sync
------------------

A snapshot tree sync works like a versioned tree sync, but versions are
never updated after their initial release. "STATUS" marker files are
used to indicate when a tree is completed.

The big advantage of snapshot tree syncs is that once a tree has been
marked as complete locally, it never needs to be checked against the
upstream site again.


Snapshot Delta Sync
-------------------

Delta syncs actually require an upstream Pulp server (rather than just
an rsync daemon) and use a chain of 3 custom Pulp plugins.

At the upstream site, rsync is run in batch mode to generate delta files
to update from the previous version of the tree to the latest snapshot.

This delta files are then published for retrieval by the downstream servers.

The downstream servers first check if a delta file is available that
is applicable to the most recent version of the tree they have completed
locally. If it exists, they download and apply it. Otherwise, they fall
back on doing a full synchronisation via rsync (i.e. the same process as an
ordinary snapshot tree sync)
