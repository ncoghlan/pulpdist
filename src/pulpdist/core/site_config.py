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
"""Config definitions and helpers for pulpdist site configuration"""
import collections

from . import validation, site_sql, repo_config, sync_config, mirror_config

def _display_id(config):
    """Gets a nicely formatted Repo ID from a repo configuration"""
    notes = config["notes"].get("pulpdist")
    mirror_id = notes.get("mirror_id") if notes else None
    if mirror_id is not None:
        return "{0}({1})".format(mirror_id, notes["site_id"])
    return config["repo_id"]

class PulpRepo(collections.namedtuple("PulpRepo", "id display_id config")):
    @classmethod
    def from_config(cls, config):
        return cls(config["repo_id"], _display_id(config), config)

def check_path_mapping():
    return validation.check_mapping_items(validation.check_simple_id(),
                                          validation.check_path(allow_none=True),
                                          allow_none=True)

class RemoteServerConfig(validation.ValidatedConfig):
    _SPEC =  {
        u"server_id": validation.check_simple_id(),
        u"name": validation.check_text(),
        u"dns": validation.check_text(),
        u"old_daemon": validation.check_type(int),
        u"rsync_port": validation.check_type(int, allow_none=True),
    }
    _DEFAULTS =  {
        u"old_daemon": False,
        u"rsync_port": None,
    }


class RemoteSourceConfig(validation.ValidatedConfig):
    _SPEC =  {
        u"source_id": validation.check_simple_id(),
        u"server_id": validation.check_simple_id(),
        u"name": validation.check_text(),
        u"remote_path": validation.check_text(),
        u"listing_suffix": validation.check_rsync_filter(),
    }


class RemoteTreeConfig(validation.ValidatedConfig):
    _SPEC =  {
        u"tree_id": validation.check_simple_id(),
        u"source_id": validation.check_simple_id(),
        u"name": validation.check_text(),
        u"description": validation.check_text(allow_none=True),
        u"tree_path": validation.check_path(),
        u"sync_hours": validation.check_type(int, allow_none=True),
        u"sync_type": validation.check_value(sync_config.SYNC_TYPES),
        u"exclude_from_sync": validation.check_rsync_filter_sequence(),
        u"sync_filters": validation.check_rsync_filter_sequence(),
        u"listing_pattern": validation.check_rsync_filter(allow_none=True),
        u"listing_prefix": validation.check_rsync_filter(allow_none=True),
        u"latest_link": validation.check_path(allow_none=True),
        u"exclude_from_listing": validation.check_rsync_filter_sequence(),
        u"listing_filters": validation.check_rsync_filter_sequence(),
    }
    _DEFAULTS =  {
        u"description": None,
        u"sync_hours": None,
        u"exclude_from_sync": [],
        u"sync_filters": [],
        u"listing_pattern": None,
        u"listing_prefix": None,
        u"latest_link": None,
        u"exclude_from_listing": [],
        u"listing_filters": [],
    }

    @classmethod
    def post_validate(self, config):
        pattern = config[u"listing_pattern"]
        prefix = config[u"listing_prefix"]
        sync_type = config[u"sync_type"]
        if pattern is None:
            if prefix is None and sync_config.retrieves_listing(sync_type):
                validation.fail_validation("Must set either listing_prefix or listing_pattern")
        elif prefix is not None:
            validation.fail_validation("Cannot set both listing_prefix and listing_pattern")


class LocalMirrorConfig(validation.ValidatedConfig):
    _SPEC =  {
        u"mirror_id": validation.check_simple_id(),
        u"tree_id": validation.check_simple_id(),
        u"site_id": validation.check_simple_id(),
        u"name": validation.check_text(allow_none=True),
        u"description": validation.check_text(allow_none=True),
        u"mirror_path": validation.check_path(allow_none=True),
        u"exclude_from_sync": validation.check_rsync_filter_sequence(),
        u"sync_filters": validation.check_rsync_filter_sequence(),
        u"exclude_from_listing": validation.check_rsync_filter_sequence(),
        u"listing_filters": validation.check_rsync_filter_sequence(),
        u"notes": validation.check_type(dict, allow_none=True),
        u"enabled": validation.check_type(int),
        u"dry_run_only": validation.check_type(int),
        u"delete_old_dirs": validation.check_type(int),
        u"sync_latest_only": validation.check_type(int),
    }
    _DEFAULTS =  {
        u"site_id": "default",
        u"name": None,
        u"description": None,
        u"mirror_path": None,
        u"exclude_from_sync": [],
        u"sync_filters": [],
        u"exclude_from_listing": [],
        u"listing_filters": [],
        u"notes": {},
        u"enabled": False,
        u"dry_run_only": False,
        u"delete_old_dirs": False,
        u"sync_latest_only": False,
    }

class SiteSettingsConfig(validation.ValidatedConfig):
    _SPEC =  {
        u"site_id": validation.check_simple_id(),
        u"name": validation.check_text(),
        u"storage_prefix": validation.check_text(),
        u"exclude_from_sync": validation.check_rsync_filter_sequence(),
        u"exclude_from_listing": validation.check_rsync_filter_sequence(),
        u"server_prefixes": check_path_mapping(),
        u"source_prefixes": check_path_mapping(),
    }
    _DEFAULTS =  {
        u"exclude_from_sync": [],
        u"exclude_from_listing": [],
        u"server_prefixes": {},
        u"source_prefixes": {},
    }

class SiteConfig(validation.ValidatedConfig):
    _SPEC = {
        u"SITE_SETTINGS": [SiteSettingsConfig],
        u"LOCAL_MIRRORS": [LocalMirrorConfig],
        u"REMOTE_TREES": [RemoteTreeConfig],
        u"REMOTE_SOURCES": [RemoteSourceConfig],
        u"REMOTE_SERVERS": [RemoteServerConfig],
        u"RAW_REPOS": [repo_config.RepoConfig],
    }
    _DEFAULTS = {
        u"SITE_SETTINGS": [],
        u"LOCAL_MIRRORS": [],
        u"REMOTE_TREES": [],
        u"REMOTE_SOURCES": [],
        u"REMOTE_SERVERS": [],
        u"RAW_REPOS": [],
    }

    _SQL_LOAD_ORDER = (
        (u"REMOTE_SERVERS", site_sql.RemoteServer),
        (u"REMOTE_SOURCES", site_sql.RemoteSource),
        (u"REMOTE_TREES", site_sql.RemoteTree),
        (u"SITE_SETTINGS", site_sql.SiteSettings),
        (u"LOCAL_MIRRORS", site_sql.LocalMirror),
    )

    def __init__(self, *args, **kwds):
        super(SiteConfig, self).__init__(*args, **kwds)
        self._db_session_factory = None

    @property
    def repo_config(self):
        if self._repo_config is None:
            self.validate()
        return self._repo_config

    def _init_db(self):
        self._db_session_factory = site_sql.in_memory_db()

    def _get_db_session(self):
        if self._db_session_factory is None:
            self.validate()
        return self._db_session_factory()

    def _populate_db(self):
        # Always start with a fresh DB instance
        self._init_db()
        # Populate with data
        config = self.config
        for key, model in self._SQL_LOAD_ORDER:
            for model_data in config[key]:
                db_session = self._get_db_session()
                db_session.add(model.from_mapping(model_data))
                try:
                    db_session.commit()
                except site_sql.IntegrityError as exc:
                    validation.fail_validation(exc)
        self._convert_raw_repos()
        self._convert_mirrors()

    def _store_repo(self, config):
        db_session = self._get_db_session()
        db_session.add(site_sql.PulpRepository.from_mapping(config))
        try:
            db_session.commit()
        except site_sql.IntegrityError as exc:
            validation.fail_validation(exc)

    def _convert_raw_repos(self):
        raw_repos = self.config["RAW_REPOS"]
        for repo_data in raw_repos:
            repo_details = {
                "repo_id": repo_data["repo_id"],
                "config": repo_data,
            }
            self._store_repo(repo_details)

    def _convert_mirror(self, mirror):
        raw_data = mirror_config.make_repo(mirror)
        repo_data = repo_config.RepoConfig.ensure_validated(raw_data)
        repo_details = repo_data["notes"]["pulpdist"].copy()
        repo_details["repo_id"] = repo_data["repo_id"]
        repo_details["config"] = repo_data
        self._store_repo(repo_details)

    def _convert_mirrors(self):
        mirrors = self.query_mirrors()
        for m in mirrors:
            self._convert_mirror(m)

    def _validate_spec(self):
        super(SiteConfig, self).validate()

    def validate(self):
        self._validate_spec()
        self._populate_db()

    def query_mirrors(self, *args, **kwds):
        """Returns an SQLAlchemy query result. See site_sql.query_mirrors"""
        db_session = self._get_db_session()
        return site_sql.query_mirrors(db_session, *args, **kwds)

    def query_repos(self, *args, **kwds):
        """Returns an SQLAlchemy query result. See site_sql.query_repos"""
        db_session = self._get_db_session()
        return site_sql.query_repos(db_session, *args, **kwds)

    def get_repo_configs(self, *args, **kwds):
        repos = self.query_repos(*args, **kwds)
        return [repo.config for repo in repos]


