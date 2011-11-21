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

TREE_SYNC_CONFIG = {
    "tree_name": validation.check_type(str),
    "remote_server": validation.check_hostname(),
    "remote_path": validation.check_remote_path(),
    "excluded_files": validation.check_seq(validation.check_rsync_filter()),
    "sync_filters": validation.check_seq(validation.check_rsync_filter()),
    "bandwidth_limit": validation.check_type(int),
    "is_test_run": validation.check_type(int),
    "old_remote_daemon": validation.check_type(int),
    "rsync_port": validation.check_type(int),
    "log_path": validation.check_path(),
}

VERSIONED_SYNC_CONFIG = TREE_SYNC_CONFIG + {
    "version_pattern": validation.check_rsync_filter(),
    "excluded_versions": validation.check_seq(validation.check_rsync_filter()),
}

SNAPSHOT_SYNC_CONFIG = dict(
    tree_name = "Snapshot Tree",
    remote_server = "localhost",
    remote_path = "/test_data/versioned/",
    version_pattern = "relevant*",
    excluded_versions = "relevant-but*".split(),
    excluded_files = "*skip*".split(),
    sync_filters = "exclude_irrelevant/ exclude_dull/".split(),
    log_path = _default_log
)
