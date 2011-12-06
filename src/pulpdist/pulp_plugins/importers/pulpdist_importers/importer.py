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
import tempfile

try:
    from pulpdist.core import sync_trees, validation
except ImportError:
    # Hack to allow running from a source checkout
    import os, sys
    # We're in pulpdist/pulp_plugins/importers/pulpdist_importers, so need to go up 4 dirs
    this_dir = os.path.realpath(os.path.dirname(__file__))
    plugin_dir = os.path.abspath(this_dir + "/../../../..")
    sys.path.append(plugin_dir)
    from pulpdist.core import sync_trees, validation


from pulp.server.content.plugins.importer import Importer

class _BaseImporter(Importer):
    CONTENT_TYPES = ["tree"]

    @classmethod
    def metadata(cls):
        return {
            "id" : cls.PULP_ID,
            "display_name": cls.DISPLAY_NAME,
            "types" : cls.CONTENT_TYPES
        }

    def _build_sync_config(self, config):
        sync_config = self.SYNC_COMMAND.CONFIG_TYPE()
        for key in sync_config:
            setting = config.get(key)
            if setting is not None:
                sync_config.config[key] = setting
        return sync_config

    def validate_config(self, repo, config):
        sync_config = self._build_sync_config(config)
        sync_config.validate()
        return True

    def sync_repo(self, repo, sync_conduit, config):
        sync_config = self._build_sync_config(config)
        with tempfile.NamedTemporaryFile() as sync_log:
            sync_config.config["log_path"] = sync_log.name
            command = self.SYNC_COMMAND(sync_config.config)
            # TODO: Refactor to support progress reporting
            # TODO: Refactor to populate content unit metadata
            sync_info = command.run_sync()
            sync_log_data = sync_log.read()
        summary = {
            "start_time": sync_info[0].isoformat(),
            "finish_time": sync_info[1].isoformat(),
            "stats": sync_info[2]._asdict(),
        }
        details = {
            "sync_log": sync_log_data,
        }
        return sync_conduit.build_report(summary, details)

class SimpleTreeImporter(_BaseImporter):
    PULP_ID = "simple_tree"
    DISPLAY_NAME = "Simple Tree Importer"
    SYNC_COMMAND = sync_trees.SyncTree


class VersionedTreeImporter(_BaseImporter):
    PULP_ID = "versioned_tree"
    DISPLAY_NAME = "Versioned Tree Importer"
    SYNC_COMMAND = sync_trees.SyncVersionedTree


class SnapshotTreeImporter(_BaseImporter):
    PULP_ID = "snapshot_tree"
    DISPLAY_NAME = "Snapshot Tree Importer"
    SYNC_COMMAND = sync_trees.SyncSnapshotTree


class SnapshotDeltaImporter(_BaseImporter):
    PULP_ID = "snapshot_delta"
    DISPLAY_NAME = "Snapshot Delta Importer"
    CONTENT_TYPES = ["tree_delta"]


class DeltaTreeImporter(_BaseImporter):
    PULP_ID = "delta_tree"
    DISPLAY_NAME = "Delta Tree Importer"
