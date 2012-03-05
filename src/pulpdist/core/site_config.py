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
from . import validation, site_sql, repo_config, sync_config, mirror_config

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
        u"excluded_files": validation.check_rsync_filter_sequence(),
        u"sync_filters": validation.check_rsync_filter_sequence(),
        u"version_pattern": validation.check_rsync_filter(allow_none=True),
        u"version_prefix": validation.check_path(allow_none=True),
        u"excluded_versions": validation.check_rsync_filter_sequence(),
        u"version_filters": validation.check_rsync_filter_sequence(),
    }
    _DEFAULTS =  {
        u"description": None,
        u"sync_hours": None,
        u"excluded_files": [],
        u"sync_filters": [],
        u"version_pattern": None,
        u"version_prefix": None,
        u"excluded_versions": [],
        u"version_filters": [],
    }

    @classmethod
    def post_validate(self, config):
        pattern = config[u"version_pattern"]
        prefix = config[u"version_prefix"]
        sync_type = config[u"sync_type"]
        if pattern is None:
            if prefix is None and sync_config.requires_version(sync_type):
                validation.fail_validation("Must set either version_prefix or version_pattern")
        elif prefix is not None:
            validation.fail_validation("Cannot set both version_prefix and version_pattern")


class LocalMirrorConfig(validation.ValidatedConfig):
    _SPEC =  {
        u"mirror_id": validation.check_simple_id(),
        u"tree_id": validation.check_simple_id(),
        u"site_id": validation.check_simple_id(),
        u"name": validation.check_text(allow_none=True),
        u"description": validation.check_text(allow_none=True),
        u"mirror_path": validation.check_path(allow_none=True),
        u"excluded_files": validation.check_rsync_filter_sequence(),
        u"sync_filters": validation.check_rsync_filter_sequence(),
        u"excluded_versions": validation.check_rsync_filter_sequence(),
        u"version_filters": validation.check_rsync_filter_sequence(),
        u"notes": validation.check_type(dict, allow_none=True),
        u"enabled": validation.check_type(int),
        u"dry_run_only": validation.check_type(int),
        u"delete_old_dirs": validation.check_type(int),
    }
    _DEFAULTS =  {
        u"site_id": "default",
        u"name": None,
        u"description": None,
        u"mirror_path": None,
        u"excluded_files": [],
        u"sync_filters": [],
        u"excluded_versions": [],
        u"version_filters": [],
        u"notes": {},
        u"enabled": False,
        u"dry_run_only": False,
        u"delete_old_dirs": False,
    }

class SiteSettingsConfig(validation.ValidatedConfig):
    _SPEC =  {
        u"site_id": validation.check_simple_id(),
        u"name": validation.check_text(),
        u"storage_prefix": validation.check_text(),
        u"version_suffix": validation.check_rsync_filter(),
        u"default_excluded_files": validation.check_rsync_filter_sequence(),
        u"default_excluded_versions": validation.check_rsync_filter_sequence(),
        u"server_prefixes": check_path_mapping(),
        u"source_prefixes": check_path_mapping(),
    }
    _DEFAULTS =  {
        u"default_excluded_files": [],
        u"default_excluded_versions": [],
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
        u"RAW_TREES": [repo_config.RepoConfig],
    }

    _SQL_LOAD_ORDER = (
        (u"REMOTE_SERVERS", site_sql.RemoteServer),
        (u"REMOTE_SOURCES", site_sql.RemoteSource),
        (u"REMOTE_TREES", site_sql.RemoteTree),
        (u"SITE_SETTINGS", site_sql.SiteSettings),
        (u"LOCAL_MIRRORS", site_sql.LocalMirror),
        (u"RAW_TREES", site_sql.PulpRepository),
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

    def _validate_spec(self):
        super(SiteConfig, self).validate()

    def validate(self):
        self._validate_spec()
        self._populate_db()

    def _get_db_session(self):
        if self._db_session_factory is None:
            self.validate()
        return self._db_session_factory()

    def query_mirrors(self, *args, **kwds):
        """Returns an SQLAlchemy query result. See site_sql.query_mirrors"""
        db_session = self._get_db_session()
        return site_sql.query_mirrors(db_session, *args, **kwds)

    def convert_mirror(self, mirror):
        repo_data = mirror_config.make_repo(mirror)
        return repo_config.RepoConfig.ensure_validated(repo_data)

    def make_repo_configs(self, *args, **kwds):
        db_session = self._get_db_session()
        # Query populated DB
        mirrors = self.query_mirrors(*args, **kwds)
        repo_configs = [self.convert_mirror(m) for m in mirrors]
        repo_configs.extend(self.config["RAW_TREES"])
        return repo_configs


