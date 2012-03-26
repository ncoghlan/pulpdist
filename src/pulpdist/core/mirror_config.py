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
"""Convert from a site mirror config to a PulpDist repo config"""

from fnmatch import fnmatch
import os.path

def make_repo(mirror):
    return MirrorConverter(mirror).config

def make_repo_id(mirror_id, site_id):
    """Derive a Pulp repo ID from a mirror ID and a site ID"""
    return u"{0}__{1}".format(mirror_id, site_id)

class MirrorConverter(object):
    def __init__(self, mirror):
        self.mirror = mirror
        self.config = {
            u"repo_id": make_repo_id(mirror.mirror_id, mirror.site_id),
            u"display_name": mirror.name or mirror.tree.name,
            u"description": mirror.description or mirror.tree.description
        }
        self.build_notes()
        self.build_importer_config()

    def build_notes(self):
        mirror = self.mirror
        pulpdist = {
            u"sync_hours": mirror.tree.sync_hours,
            u"mirror_id": mirror.mirror_id,
            u"site_id": mirror.site_id,
            u"tree_id": mirror.tree_id,
            u"source_id": mirror.tree.source_id,
            u"server_id": mirror.tree.source.server_id
        }
        notes = {u"pulpdist": pulpdist}
        notes.update(mirror.notes)
        self.config[u"notes"] = notes

    def build_importer_config(self):
        mirror = self.mirror
        sync_type = mirror.tree.sync_type
        tree_type = sync_type + u"_tree"
        config_builder = getattr(self, u"_build_{0}_config".format(sync_type))
        self.config[u"importer_type_id"] = tree_type
        self.config[u"importer_config"] = config_builder()

    def _build_simple_config(self):
        mirror = self.mirror
        tree = mirror.tree
        source = tree.source
        server = source.server
        site = mirror.site
        default_site = mirror.default_site
        config = {
            u"tree_name": self.config["repo_id"],
            u"remote_server": server.dns,
            u"old_remote_daemon": server.old_daemon,
            u"enabled": mirror.enabled,
            u"dry_run_only": mirror.dry_run_only,
        }
        sync_filters = mirror.sync_filters + tree.sync_filters
        config[u"sync_filters"] = sync_filters
        exclude_from_sync = list(set(mirror.exclude_from_sync
                                     + tree.exclude_from_sync
                                     + site.exclude_from_sync
                                     + default_site.exclude_from_sync))
        config[u"exclude_from_sync"] = exclude_from_sync
        mirror_path = mirror.mirror_path
        if mirror_path is None:
            mirror_path = tree.tree_path
        server_prefixes = site.server_prefixes
        server_prefixes.update(default_site.server_prefixes)
        server_prefix = server_prefixes.get(server.server_id, u"")
        source_prefixes = site.source_prefixes
        source_prefixes.update(default_site.source_prefixes)
        source_prefix = source_prefixes.get(source.source_id, u"")
        config[u"local_path"] = os.path.join(u"/",
                                            site.storage_prefix,
                                            server_prefix,
                                            source_prefix,
                                            mirror_path,
                                            u"")
        config[u"remote_path"] = os.path.join(u"/",
                                             source.remote_path,
                                             tree.tree_path,
                                             u"")
        rsync_port = server.rsync_port
        if rsync_port is not None:
            config[u"rsync_port"] = rsync_port
        return config

    def _build_versioned_config(self):
        mirror = self.mirror
        tree = mirror.tree
        site = mirror.site
        default_site = mirror.default_site
        source = tree.source
        config = self._build_simple_config()
        config[u"delete_old_dirs"] = mirror.delete_old_dirs
        listing_pattern = tree.listing_pattern
        if listing_pattern is None:
            listing_pattern = tree.listing_prefix + source.listing_suffix
        config[u"listing_pattern"] = listing_pattern
        def _not_this(other_pattern):
            return fnmatch(other_pattern, listing_pattern)
        exclude_from_listing = list(set(mirror.exclude_from_listing
                                        + tree.exclude_from_listing
                                        + site.exclude_from_listing
                                        + default_site.exclude_from_listing))
        exclude_from_listing = [v for v in exclude_from_listing if _not_this(v)]
        config[u"exclude_from_listing"] = exclude_from_listing
        listing_filters = mirror.listing_filters + tree.listing_filters
        config[u"listing_filters"] = listing_filters
        return config

    def _build_snapshot_config(self):
        config = self._build_versioned_config()
        latest_link = self.mirror.tree.latest_link
        if latest_link is not None:
            config[u"latest_link_name"] = latest_link
        return config
