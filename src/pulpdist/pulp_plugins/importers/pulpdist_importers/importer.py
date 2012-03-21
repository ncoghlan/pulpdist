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
import sys
import traceback
from cStringIO import StringIO

# BZ#799203: As a workaround until the more flexible progress reporting is
# implemented in the Pulp APIs, we hardcode writing out the sync logs to
# a directory we publish over https
import os, os.path
SYNC_LOG_RELPATH = "var/www/pub/pulpdist_sync_logs"

try:
    from pulpdist.core import sync_trees, validation
    SYNC_LOG_DIR = "/" + SYNC_LOG_RELPATH
except ImportError:
    # Hack to allow running from a source checkout
    import os, sys
    # We're in src/pulpdist/pulp_plugins/importers/pulpdist_importers in Git
    # so need to go up 4 dirs to find the dir to add to sys.path
    this_dir = os.path.realpath(os.path.dirname(__file__))
    src_dir = os.path.abspath(this_dir + "/../../../..")
    sys.path.append(src_dir)
    from pulpdist.core import sync_trees, validation, util
    # And then another dir up to find where to put the sync logs
    SYNC_LOG_DIR = os.path.abspath(
                         os.path.normpath(
                             os.path.join(src_dir, '..', SYNC_LOG_RELPATH)))


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

    def _init_sync_log(self, log_name):
        log_file = log_name + ".log"
        log_path = os.path.join(SYNC_LOG_DIR, log_file)
        # This relies on the use of unique tree names and Pulp serialising
        # sync requests to avoid a race condition...
        if os.path.exists(log_path):
            backup_file = log_file + ".bak"
            backup_path = os.path.join(SYNC_LOG_DIR, backup_file)
            os.rename(log_path, backup_path)
        return log_path

    def _read_sync_log(self, sync_log):
        with open(sync_log) as f:
            return f.read()

    def sync_repo(self, repo, sync_conduit, config):
        sync_config = self._build_sync_config(config)
        sync_log = self._init_sync_log(repo.id)
        command = self.SYNC_COMMAND(sync_config.config, sync_log)
        try:
            # TODO: Refactor to support progress reporting
            # TODO: Refactor to populate content unit metadata
            sync_info = command.run_sync()
        except:
            et, ev, tb = sys.exc_info()
            msg = (
                "exception: {0}\n"
                "error_message: {1}\n"
                "traceback:\n{2}\n"
                "log_details:\n{3}\n"
            )
            raise RuntimeError(msg.format(et, ev,
                               traceback.format_tb(tb),
                               self._read_sync_log(sync_log)))
        result = sync_info[0]
        summary = {
            "result": result,
            "start_time": sync_info[1].isoformat(),
            "finish_time": sync_info[2].isoformat(),
            "stats": sync_info[3]._asdict(),
        }
        details = {
            "sync_log": self._read_sync_log(sync_log),
        }
        report = sync_conduit.build_report(summary, details)
        return report

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
