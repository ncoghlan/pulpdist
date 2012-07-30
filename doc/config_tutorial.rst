.. _site-config-tutorial:

Site Configuration Tutorial
===========================

The following file is an example site definition provided in the PulpDist
source tree (as ``misc/example_site.json``) for demonstration purposes:

.. literalinclude:: ../misc/example_site.json
   :language: js

The example configuration is actually based on the PulpDist test suite - it
is designed to exercise most of the major features of the PulpDist plugins in a
single comprehensive scenario (some other key features, such as the use of
PROTECTED files to prevent the deletion of directories, or the creation of
symlinks to the most recent snapshot directory, are testing by setting up
the standard scenario and adjusting some of the settings or the filesystem
layout appropriately). This section aims to break the example down
into components and explain how each of them works.


Working with the Example Configuration
--------------------------------------

The example configuration is designed to be used with a local rsync daemon
and the ``misc/create_demo_tree.py`` script in the source repo.

Using ``/var/pulpdist_example_data`` as the location for our demonstration
tree, then ``/etc/rsyncd.conf`` should look something like this::

   log file = /var/log/rsyncd.log

   [demo]
   comment="PulpDist Example Data Source"
   path=/var/pulpdist_example_data

With ``pulpdist`` installed (or else with the ``src`` directory in a
source checkout as the current directory), the following command will
create a demonstration tree::

   python create_demo_tree.py /var/pulpdist_example_data

The file tree created is laid out as follows (see below for details of the
subtree layout represented by ``...``)::

   simple/
     ...
   versioned/
     ignored/
       ...
     relevant-1/
       ...
     relevant-2/
       ...
     relevant-3/
       ...
     relevant-4/
       ...
     relevant-but-not-really/
       ...
   snapshot/
     ignored/
       ...
     relevant-1/
       STATUS
       ...
     relevant-2/
       STATUS
       ...
     relevant-3/
       ...
     relevant-4/
       STATUS
       ...
     relevant-but-not-really/
       ...

The common subtrees all look like the following::

   data.txt
   data2.txt
   skip.txt
   subdir/
     data.txt
     data2.txt
     skip.txt
     subdir/
       data.txt
       data2.txt
       skip.txt
   subdir2/
     data.txt
     data2.txt
     dull/
       data.txt
       data2.txt
       skip.txt
     skip.txt

All ``STATUS`` files contain the text ``FINISHED`` (and nothing else), while
the example text files contain the text ``PulpDist test data!``.


The Raw Repo Definition
-----------------------

The example configuration includes a single
:ref:`Raw Repo Definition <raw-repo-def>`. For ease
of reference, it is reproduced here::

   "RAW_REPOS": [
     {
       "repo_id": "raw_sync",
       "display_name": "Raw Sync Demo",
       "description": "Demonstration of raw sync configuration in site config",
       "notes": {
         "pulpdist": {
           "sync_hours": 24
         },
         "site_custom": {
           "origin": "PulpDist example repository"
         }
       },
       "importer_type_id": "simple_tree",
       "importer_config": {
         "tree_name": "Raw Simple Tree",
         "remote_server": "localhost",
         "remote_path": "/demo/simple/",
         "local_path": "/var/www/pub/sync_demo_raw/",
         "exclude_from_sync": ["*skip*"],
         "sync_filters": ["exclude_irrelevant/", "exclude_dull/"]
       }
     }
   ]

Raw repos map almost directly to the Pulp settings for the corresponding
plugin. This has the advantage of making them entirely self contained and
very flexible, but also makes their configuration very repetitive if multiple
trees are being mirrored from the same source location.

The first three fields, ``repo_id``, ``display_name`` and ``description``
are mainly of significance for humans. The repo ID is the unique string
identifier used to refer to this repository in the command line interface,
while the display name and description are shown in the web interface.

The ``notes`` field uses a feature of Pulp that allows arbitrary additional
information to be associated with each repository. The ``site_custom`` data is
just there as an example, but the ``pulpdist`` metadata section is used to
control interaction with command line client. In this case, the
value ``24`` means that the ``python -m pulpdist.manage_repos cron_sync``
command will synchronise this repo at midnight each day if synchronisation
is enabled on the repo (like all trees in the example configuration, this
one has synchronisation disabled by default).

The ``importer_type_id`` field indicates which kind of synchronisation
operation is being defined. The value of ``simple_tree`` indicates that this
configuration entry will set up a :ref:`simple-tree-sync` on the server.

Finally, the ``importer_config`` field actually sets up the synchronisation
operation. In this case, a simple tree sync maps directly to a single call to
rsync, so there isn't a great deal to be configured.

The ``tree_name`` value (along with ``repo_id``) will appear in the sync
operation logs created by the server.

The ``remote_server`` and ``remote_path`` operations are used to
identify the location of the source rsync daemon (rsync over ssh is not
currently supported). The ``local_path`` entry states exactly where to
save the mirrored files. For the example configuration, this means files
will be retrieved from ``rsync://localhost/demo/simple/`` and saved to
``/var/www/pub/sync_demo_raw`` (the Pulp plugins run as the Apache user, and
saving the files to ``pub`` makes it easy to share them again).

The last two entries are a little more interesting, as they map to rsync's
filtering options. Any files or directories mentioned in ``exclude_from_sync``
are passed via rsync's ``--exclude`` option, while those mentioned in
``sync_filters`` are passed with the ``--filter`` option. This offers a great
deal of flexibility in determining exactly what gets copied from the data
source into the local mirror.

Synchronization Behaviour
^^^^^^^^^^^^^^^^^^^^^^^^^

The effect of this configuration is that, after running the following two
commands::

    python -m pulpdist.manage_repos enable --repo raw_sync --force
    python -m pulpdist.manage_repos sync --repo raw_sync --force

The following filtered tree layout should be seen in
``/var/www/pub/sync_demo_raw``::

   data.txt
   data2.txt
   subdir/
     data.txt
     data2.txt
     subdir/
       data.txt
       data2.txt
   subdir2/
     data.txt
     data2.txt


Local Mirror Definition: Simple Tree
------------------------------------

Where a raw repo definition aims to include all the information needed to
configure the rsync task directly, local mirror definitions are designed
to work as part of a wider mirroring network, where various upstream
servers publish trees for consumption by downstream clients. A local
mirror definition is converted to a raw repo definition by the command line
client before being uploaded to the Pulp server at a site.

The example configuration includes a number of 
:ref:`Local Mirror Definitions <local-mirror-def>`.To introduce the
concepts involved, we'll first review the simplest of the definitions, which
describes a :ref:`simple-tree-sync` task, just like the example raw repo
definition.

Defining the Local Mirror
^^^^^^^^^^^^^^^^^^^^^^^^^

The basic mirror definition appears in the ``LOCAL_MIRRORS`` section of the
configuration file::

  "LOCAL_MIRRORS": [
    {
      "mirror_id": "simple_sync",
      "tree_id": "simple_sync",
      "exclude_from_sync": ["*skip*"],
      "sync_filters": ["exclude_irrelevant/"],
      "notes": {
        "basic": "note",
        "site_custom": {
          "origin": "PulpDist example repository"
        }
      }
    }
  ]

This example creates a local mirror named ``simple_sync`` at the default site
(see below for more on sites), which will be a copy of the remote tree
``simple_sync``. While the mirror and the remote tree have the same name in
the example, that isn't a requirement in general.

The ``notes`` entry just defines a few arbitrary notes that will be added to
the tree definition. This can be used to record additional information about
the mirror, such as the initial rationale for creating it.

The ``exclude_from_sync`` and ``sync_filters`` entries contribute to the
filter settings in the derived raw repo definition.

A local mirror definition can actually override most of the settings
defined for the remote tree being mirrored. However, this particular
example doesn't do that. See the :ref:`config reference <local-mirror-def>`
for details.


Defining the Remote Tree
^^^^^^^^^^^^^^^^^^^^^^^^

The ``tree_id`` entry names a particular
:ref:`Remote Tree Definition <remote-tree-def>` in the ``REMOTE_TREES``
section::

  "REMOTE_TREES": [
    {
      "tree_id": "simple_sync",
      "name": "Simple Sync Demo",
      "description": "Demonstration of the simple tree sync plugin",
      "tree_path": "simple",
      "sync_type": "simple",
      "sync_hours": 0,
      "source_id": "sync_demo"
    }
  ]

The ``tree_id`` is just a unique identifier for the tree, while the ``name``
and ``description`` fields are used for display to users.

The ``tree_path`` defines the name of the directory to be synchronised,
relative to the base location defined by the ``source_id``.

It is expected that this configuration format will eventually be expanded
to include a list of alternate sources for the tree, but that feature is
not yet supported.

The ``sync_type`` setting selects the specific importer plugin to be used.
Currently only PulpDist provided plugins are supported, but this may
change in future versions.

As in the raw repo example, the ``sync_hours`` ties into the ``cron_sync``
scheduling command. In this case, a setting of ``0`` servers to disable
automatic synchronisation, even if synchronisation is enabled for the repo.

Most of the settings in the tree definition are inherited by local mirrors
that don't override them. See the :ref:`config reference <remote-tree-def>`
for details.


Defining the Remote Source
^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``source_id`` entry names a particular
:ref:`Remote Source Definition <remote-source-def>` in the
``REMOTE_SOURCES`` section::

  "REMOTE_SOURCES": [
    {
      "source_id": "sync_demo",
      "server_id": "demo_server",
      "name": "Sync Demo Trees",
      "remote_path": "demo",
      "listing_suffix": "*"
    }
  ]

The ``source_id`` is just a unique identifier for the source, while the
``name`` field is intended for display to users.

The ``remote_path`` setting defines an the leading path component to use
for the remote path when deriving the raw repo definition.

The ``server-id`` defines the rsync server that hosts the content provided
by this source.

The ``listing_suffix`` isn't relevant for a simple tree definition, but
can be of significance for ``versioned`` and ``snapshot`` trees. It will
be discussed in more detail later in the tutorial.

See the :ref:`config reference <remote-source-def>` for additional
options and details.

Defining the Remote Server
^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``server_id`` entry names a particular
:ref:`Remote Server Definition <remote-server-def>` in the
``REMOTE_SERVERS`` section::

  "REMOTE_SERVERS": [
    {
      "server_id": "demo_server",
      "name": "Sync Demo Server",
      "dns": "localhost"
    }
  ]

The ``server_id`` is just a unique identifier for the source, while the
``name`` field is intended for display to users.

The ``dns`` field is either a hostname or IP address for the source
rsync server. 

See the :ref:`config reference <remote-server-def>` for additional
options and details.

Defining the Local Site
^^^^^^^^^^^^^^^^^^^^^^^

A local mirror definition may include a ``site_id`` setting that names
a particular local site configuration to be used when deriving the raw
repo definition. If no specific site is named, then the default site
definition is used. The default site definition is also used to provide
default values that are used when a specific site definition doesn't
replace them with more specific values.

The example configuration contains only the default
:ref:`Site Definition <site-def>` in the ``SITE_SETTINGS`` section::

  "SITE_SETTINGS": [
    {
      "site_id": "default",
      "name": "Default Site",
      "storage_prefix": "/var/www/pub",
      "server_prefixes": {
        "demo_server": "sync_demo"
      },
      "source_prefixes": {
        "sync_demo": "sync_demo_trees"
      }
    }
  ]

The ``site_id`` is just a unique identifier for the site, while the
``name`` field is intended for display to users.

The ``storage_prefix`` is included in all local paths.

The ``server_prefixes`` and ``source_prefixes`` mappings are used to
map ``server_id`` and ``source_id`` values to local path components.

See the :ref:`config reference <site-def>` for additional
options and details.


Equivalent Raw Repo Definition
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A local mirror definition isn't used to configure a repo directly.
Instead, an equivalent raw repo definition is derived from the local
mirror definition and all of the related settings. The
:ref:`config reference <deriving-repo-defs>` gives an overview of this
process.

For the simple tree mirror, the equivalent definition would look like this::

     {
       "repo_id": "simple__default",
       "display_name": "Simple Sync Demo",
       "description": "Demonstration of simple tree sync plugin",
       "notes": {
          "basic": "note",
          "pulpdist": {
            "mirror_id": "simple_sync",
            "server_id": "demo_server",
            "site_id": "default",
            "source_id": "sync_demo",
            "sync_hours": 0,
            "tree_id": "simple_sync"
          },
          "site_custom": {
            "origin": "PulpDist example repository"
          }
       },
       "importer_type_id": "simple_tree",
       "importer_config": {
         "tree_name": "simple_sync__default",
         "remote_server": "localhost",
         "remote_path": "/demo/simple/",
         "local_path": "/var/www/pub/sync_demo/sync_demo_trees/simple/",
         "exclude_from_sync": ["*skip*"],
         "sync_filters": ["exclude_irrelevant/"]
       }
     }

The ``repo_id`` is a combination of the ``mirror_id`` and the ``site_id``.
This allows multiple nominal sites to be configured on the same Pulp
server without identifier conflicts.

The ``display_name`` and ``description`` in this case come directly from
the remote tree definition.

The ``notes`` are a combination of those specified in the local mirror
definition, along with those automatically created by the derivation
process. The derived notes include the identifiers for each of the
components used to derive the repo definition, along with the ``sync_hours``
setting for use by the ``cron_sync`` scheduling operation.

The ``importer_type_id`` is derived from the ``sync_type`` setting in the
remote tree definition.

The import configuration details used for a simple sync operation are
common to all supported importer plugins.

``tree_name`` is always just the dervied ``repo_id`` for the local mirror.

``remote_server`` is the ``dns`` property of the remote server definition.

``remote_path`` in this cases is a combination of the ``remote_path`` entry
in the remote source definition and the ``tree_path`` entry in the remote
tree definition.

``local_path`` is a combination of the ``storage_prefix`` from the site
settings, the prefixes for the remote server and source respectively (both
retrieved from the site settings) and finishing with the ``tree_path`` entry
from the remote tree definition (this is one of those settings where the
value from the remote tree definition is used if the local mirror
definition doesn't override it).

Finally, the ``exclude_from_sync`` and ``sync_filters`` settings are taken
directly from the local mirror definition, as none of the other components
involved in this particular mirror configuration include any of the
filtering options.


Synchronization Behaviour
^^^^^^^^^^^^^^^^^^^^^^^^^

The effect of this configuration is that, after running the following two
commands::

    python -m pulpdist.manage_repos enable --mirror simple_sync --force
    python -m pulpdist.manage_repos sync --mirror simple_sync --force

The following filtered tree layout should be seen in
``/var/www/pub/sync_demo/sync_demo_trees/simple``::

   data.txt
   data2.txt
   subdir/
     data.txt
     data2.txt
     subdir/
       data.txt
       data2.txt
   subdir2/
     data.txt
     data2.txt
     dull/
       data.txt
       data2.txt


Why Use Mirror Definitions?
^^^^^^^^^^^^^^^^^^^^^^^^^^^

From the worked example, it may seem that mirror definitions are actually
harder to use than the equivalent raw repo definitions. If you only want to
mirror a single tree, this is true (that's why the option to provide a
raw repo definition instead exists).

The intended use case for PulpDist, however, is for an internal mirroring
network, where any given rsync server will be publishing multiple trees,
and any given site will be downloading multiple trees (potentially from
different sources).

The advantage of the mirror definition format is that it allows this
arrangement to be modelled directly - when setting up a new local mirror
for an existing remote tree, all you need to know is the id of the
remote tree and the id of the site where the mirror is being created,
rather than all of the details necessary to create the raw repo definition
by hand. Avoiding the data duplication also helps ensure consistency
between mirrors, and also makes various data changes substantially easier
(for example, changing the hostname of a particular upstream rsync server).


Local Mirror Definition: Versioned Tree
---------------------------------------

Coming soon!


Local Mirror Definition: Snapshot Tree
--------------------------------------

Coming soon!