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
"""Config definitions and helpers for pulpdist importer plugins"""
from . import validation

def _updated(original, additions):
    new = original.copy()
    new.update(additions)
    return new

class TreeSyncConfig(object):
    _SPEC = {
        "tree_name": validation.check_type(str),
        "remote_server": validation.check_host(),
        "remote_path": validation.check_remote_path(),
        "local_path": validation.check_path(),
        "excluded_files": validation.check_sequence(validation.check_rsync_filter()),
        "sync_filters": validation.check_sequence(validation.check_rsync_filter()),
        "bandwidth_limit": validation.check_type(int),
        "is_test_run": validation.check_type(int),
        "old_remote_daemon": validation.check_type(int),
        "rsync_port": validation.check_type(int, allow_none=True),
        "log_path": validation.check_path(allow_none=True),
    }
    _DEFAULTS = {
        "excluded_files": (),
        "sync_filters": (),
        "bandwidth_limit": 0,
        "is_test_run": False,
        "old_remote_daemon": False,
        "rsync_port": None,
        "log_path": None,
    }

    def __init__(self, config):
        self.config = saved = self._DEFAULTS.copy()
        saved.update(config)

    def validate(self):
        validation.validate_config(self.config, self._SPEC)

class VersionedSyncConfig(TreeSyncConfig):
    _SPEC = _updated(TreeSyncConfig._SPEC, {
        "version_pattern": validation.check_rsync_filter(),
        "excluded_versions": validation.check_sequence(validation.check_rsync_filter()),
        "subdir_filters": validation.check_sequence(validation.check_rsync_filter()),
    })
    _DEFAULTS = _updated(TreeSyncConfig._DEFAULTS, {
        "version_pattern": '*',
        "excluded_versions": (),
        "subdir_filters": (),
    })

class SnapshotSyncConfig(VersionedSyncConfig):
    _SPEC = _updated(VersionedSyncConfig._SPEC, {
        "latest_link_name": validation.check_path(allow_none=True),
    })
    _DEFAULTS = _updated(VersionedSyncConfig._DEFAULTS, {
        "latest_link_name": None,
    })

    def __init__(self, config):
        super(SnapshotSyncConfig, self).__init__(config)
        excluded_files = list(self.config["excluded_files"])
        excluded_files += ["STATUS", ".STATUS"]
        self.config["excluded_files"] = excluded_files

