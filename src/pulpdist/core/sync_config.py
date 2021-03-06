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

SYNC_TYPES = "simple versioned snapshot".split()
RETRIEVES_LISTING = SYNC_TYPES[1:]

def retrieves_listing(sync_type):
    return sync_type in RETRIEVES_LISTING

def _updated(original, additions):
    new = original.copy()
    new.update(additions)
    return new

class TreeSyncConfig(validation.ValidatedConfig):
    _SPEC = {
        u"tree_name": validation.check_text(),
        u"remote_server": validation.check_host(),
        u"remote_path": validation.check_remote_path(),
        u"local_path": validation.check_path(),
        u"exclude_from_sync": validation.check_rsync_filter_sequence(),
        u"sync_filters": validation.check_rsync_filter_sequence(),
        u"bandwidth_limit": validation.check_type(int),
        u"dry_run_only": validation.check_type(int),
        u"old_remote_daemon": validation.check_type(int),
        u"rsync_port": validation.check_type(int, allow_none=True),
        u"enabled": validation.check_type(int),
    }
    _DEFAULTS = {
        u"exclude_from_sync": (),
        u"sync_filters": (),
        u"bandwidth_limit": 0,
        u"dry_run_only": False,
        u"old_remote_daemon": False,
        u"rsync_port": None,
        u"enabled": False,
    }

class VersionedSyncConfig(TreeSyncConfig):
    _SPEC = _updated(TreeSyncConfig._SPEC, {
        u"listing_pattern": validation.check_rsync_filter(),
        u"exclude_from_listing": validation.check_rsync_filter_sequence(),
        u"listing_filters": validation.check_rsync_filter_sequence(),
        u"delete_old_dirs": validation.check_type(int),
    })
    _DEFAULTS = _updated(TreeSyncConfig._DEFAULTS, {
        u"listing_pattern": u'*',
        u"exclude_from_listing": (),
        u"listing_filters": (),
        u"delete_old_dirs": False,
    })

class SnapshotSyncConfig(VersionedSyncConfig):
    _SPEC = _updated(VersionedSyncConfig._SPEC, {
        u"latest_link_name": validation.check_path(allow_none=True),
        u"sync_latest_only": validation.check_type(int),
    })
    _DEFAULTS = _updated(VersionedSyncConfig._DEFAULTS, {
        u"latest_link_name": None,
        u"sync_latest_only": False,
    })

    def __init__(self, config=None):
        super(SnapshotSyncConfig, self).__init__(config)
        exclude_from_sync = list(self.config[u"exclude_from_sync"])
        exclude_from_sync += [u"STATUS", u".STATUS"]
        self.config[u"exclude_from_sync"] = exclude_from_sync

