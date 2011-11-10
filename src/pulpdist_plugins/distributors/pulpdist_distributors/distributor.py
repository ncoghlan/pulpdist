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

from pulp.server.content.plugins.distributor import Distributor

def SnapshotDeltaDistributor(Distributor):
    pulp_id = "snapshot-delta"
    display_name = "Snapshot Delta Importer"
    content_types = ["tree-delta"]

    @classmethod
    def metadata(cls):
        return {
            "id" : cls.pulp_id,
            "display_name": cls.display_name,
            "types" : cls.content_types + ["sync-log"]
        }
