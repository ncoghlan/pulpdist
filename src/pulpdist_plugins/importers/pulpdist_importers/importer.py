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

from pulpdist_plugins import sync_trees
from pulp.server.content.plugins.importer import Importer

def _BaseImporter(Importer):
    content_types = ["tree"]

    @classmethod
    def metadata(cls):
        return {
            "id" : cls.pulp_id,
            "display_name": cls.display_name,
            "types" : cls.content_types + ["sync-log"]
        }
    

class SimpleTreeImporter(_BaseImporter):
    pulp_id = "simple-tree"
    display_name = "Simple Tree Importer"


class VersionedTreeImporter(_BaseImporter):
    pulp_id = "versioned-tree"
    display_name = "Versioned Tree Importer"


class SnapshotTreeImporter(_BaseImporter):
    pulp_id = "snapshot-tree"
    display_name = "Snapshot Tree Importer"


class SnapshotDeltaImporter(_BaseImporter):
    pulp_id = "snapshot-delta"
    display_name = "Snapshot Delta Importer"
    content_types = ["tree-delta"]


class DeltaTreeImporter(_BaseImporter):
    pulp_id = "delta-tree"
    display_name = "Delta Tree Importer"
