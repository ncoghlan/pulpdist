#
# Copyright (C) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

"""PulpDist importer plugins"""

try:
    from pulpdist_plugins import sync_trees
except ImportError:
    # Hack for development installations
    import os, sys
    # We're in pulpdist_plugins/importers/pulpdist_importers, so need to go up 3 dirs
    this_dir = os.path.realpath(os.path.dirname(__file__))
    plugin_dir = os.path.abspath(this_dir + "/../../..")
    sys.path.append(plugin_dir)
    from pulpdist_plugins import sync_trees
    

from pulp.server.content.plugins.importer import Importer

class _BaseImporter(Importer):
    content_types = ["tree"]

    @classmethod
    def metadata(cls):
        return {
            "id" : cls.pulp_id,
            "display_name": cls.display_name,
            "types" : cls.content_types + ["sync_log"]
        }
    

class SimpleTreeImporter(_BaseImporter):
    pulp_id = "simple_tree"
    display_name = "Simple Tree Importer"


class VersionedTreeImporter(_BaseImporter):
    pulp_id = "versioned_tree"
    display_name = "Versioned Tree Importer"


class SnapshotTreeImporter(_BaseImporter):
    pulp_id = "snapshot_tree"
    display_name = "Snapshot Tree Importer"


class SnapshotDeltaImporter(_BaseImporter):
    pulp_id = "snapshot_delta"
    display_name = "Snapshot Delta Importer"
    content_types = ["tree_delta"]


class DeltaTreeImporter(_BaseImporter):
    pulp_id = "delta_tree"
    display_name = "Delta Tree Importer"
