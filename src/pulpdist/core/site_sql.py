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
"""SQL definitions for site configuration database definition"""


import sqlalchemy as sqla
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from . import util

SYNC_TYPES = "simple versioned snapshot".split()

Base = declarative_base()

class FieldsMixin(object):
    _FIELDS = []

    @classmethod
    def from_fields(cls, *args):
        self = cls()
        for attr, val in zip(self._FIELDS, args):
            setattr(self, attr, val)
        return self

    @classmethod
    def from_mapping(cls, mapping):
        self = cls()
        for attr, val in mapping.items():
            setattr(self, attr, val)
        return self

    def __repr__(self):
        return "<{0}>".format(util.obj_repr(self, self._FIELDS))

class SyncType(Base, FieldsMixin):
    __tablename__ = "sync_types"
    _FIELDS = "sync_type".split()
    sync_type = sqla.Column(sqla.String, primary_key=True)


class RemoteServer(Base, FieldsMixin):
    __tablename__ = "remote_servers"
    _FIELDS = "server_id name dns old_daemon rsync_port".split()
    server_id = sqla.Column(sqla.String, primary_key=True)
    name = sqla.Column(sqla.String, nullable=False)
    dns = sqla.Column(sqla.String, nullable=False)
    old_daemon = sqla.Column(sqla.Boolean, default=False)
    rsync_port = sqla.Column(sqla.Integer)


class RemoteSource(Base, FieldsMixin):
    __tablename__ = "remote_sources"
    _FIELDS = "source_id server_id name remote_path".split()
    source_id = sqla.Column(sqla.String, primary_key=True)
    server_id = sqla.Column(sqla.String, sqla.ForeignKey("remote_servers.server_id"))
    name = sqla.Column(sqla.String, nullable=False)
    remote_path = sqla.Column(sqla.String, nullable=False)


class RemoteTree(Base, FieldsMixin):
    __tablename__ = "remote_trees"
    _FIELDS = """tree_id source_id name description tree_path sync_hours
                 sync_type excluded_files sync_filters version_pattern
                 version_prefix excluded_versions version_filters""".split()
    tree_id = sqla.Column(sqla.String, primary_key=True)
    source_id = sqla.Column(sqla.String, sqla.ForeignKey("remote_sources.source_id"))
    name = sqla.Column(sqla.String, nullable=False)
    description = sqla.Column(sqla.String, server_default='')
    tree_path = sqla.Column(sqla.String, nullable=False)
    sync_type = sqla.Column(sqla.String, sqla.ForeignKey("sync_types.sync_type"))
    excluded_files = sqla.Column(sqla.PickleType)
    sync_filters = sqla.Column(sqla.PickleType)
    version_pattern = sqla.Column(sqla.String)
    version_prefix = sqla.Column(sqla.String)
    excluded_versions = sqla.Column(sqla.PickleType)
    version_filters = sqla.Column(sqla.PickleType)
    sync_hours = sqla.Column(sqla.Integer)


class LocalTree(Base, FieldsMixin):
    __tablename__ = "local_trees"
    _FIELDS = """repo_id tree_id name description tree_path sync_hours
                 sync_type excluded_files sync_filters version_pattern
                 version_prefix excluded_versions version_filters""".split()
    repo_id = sqla.Column(sqla.String, primary_key=True)
    tree_id = sqla.Column(sqla.String, sqla.ForeignKey("remote_trees.tree_id"))
    name = sqla.Column(sqla.String)
    description = sqla.Column(sqla.String)
    tree_path = sqla.Column(sqla.String)
    excluded_files = sqla.Column(sqla.PickleType)
    sync_filters = sqla.Column(sqla.PickleType)
    excluded_versions = sqla.Column(sqla.PickleType)
    version_filters = sqla.Column(sqla.PickleType)
    enabled = sqla.Column(sqla.Boolean, default=False)
    dry_run_only = sqla.Column(sqla.Boolean, default=False)
    delete_old_dirs = sqla.Column(sqla.Boolean, default=False)


class SiteSettings(Base, FieldsMixin):
    __tablename__ = "site_settings"
    _FIELDS = """site_id name storage_prefix version_suffix
                 default_excluded_files default_excluded_versions""".split()
    site_id = sqla.Column(sqla.String, nullable=False, primary_key=True)
    name = sqla.Column(sqla.String, nullable=False)
    storage_prefix = sqla.Column(sqla.String, nullable=False)
    version_suffix = sqla.Column(sqla.String, server_default='')
    default_excluded_files = sqla.Column(sqla.PickleType)
    default_excluded_versions = sqla.Column(sqla.PickleType)


class ServerPrefixes(Base, FieldsMixin):
    __tablename__ = "server_prefixes"
    _FIELDS = "site_id server_id local_prefix".split()
    site_id = sqla.Column(sqla.String, sqla.ForeignKey("site_settings.site_id"), primary_key=True)
    server_id = sqla.Column(sqla.String, sqla.ForeignKey("remote_servers.server_id"), primary_key=True)
    local_prefix = sqla.Column(sqla.String, nullable=False)


class SourcePrefixes(Base, FieldsMixin):
    __tablename__ = "source_prefixes"
    _FIELDS = "site_id source_id local_prefix".split()
    site_id = sqla.Column(sqla.String, sqla.ForeignKey("site_settings.site_id"), primary_key=True)
    source_id = sqla.Column(sqla.String, sqla.ForeignKey("remote_sources.source_id"), primary_key=True)
    local_prefix = sqla.Column(sqla.String, nullable=False)


def in_memory_db():
    engine = sqla.create_engine("sqlite:///:memory:", echo=True)
    site_db = Base.metadata
    site_db.create_all(engine)
    Session = sessionmaker(engine)
    session = Session()
    session.add_all(SyncType.from_fields(sync_type) for sync_type in SYNC_TYPES)
    session.commit()
    return Session
