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
from sqlalchemy.sql import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import sessionmaker, relation, backref
from sqlalchemy.orm.collections import attribute_mapped_collection

from . import util

SYNC_TYPES = "simple versioned snapshot".split()

def _linked_from(target, backref_attr, backref_key):
    return relation(target, backref=backref(backref_attr,
                    collection_class=attribute_mapped_collection(backref_key)))

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
    server = _linked_from(RemoteServer, "sources", "source_id")
    name = sqla.Column(sqla.String, nullable=False)
    remote_path = sqla.Column(sqla.String, nullable=False)


class RemoteTree(Base, FieldsMixin):
    __tablename__ = "remote_trees"
    _FIELDS = """tree_id source_id name description tree_path sync_hours
                 sync_type excluded_files sync_filters version_pattern
                 version_prefix excluded_versions version_filters""".split()
    tree_id = sqla.Column(sqla.String, primary_key=True)
    source_id = sqla.Column(sqla.String, sqla.ForeignKey("remote_sources.source_id"))
    source = _linked_from(RemoteSource, "trees", "tree_id")
    name = sqla.Column(sqla.String, nullable=False)
    description = sqla.Column(sqla.String, server_default="")
    tree_path = sqla.Column(sqla.String, nullable=False)
    sync_hours = sqla.Column(sqla.Integer)
    sync_type = sqla.Column(sqla.String, sqla.ForeignKey("sync_types.sync_type"))
    excluded_files = sqla.Column(sqla.PickleType)
    sync_filters = sqla.Column(sqla.PickleType)
    version_pattern = sqla.Column(sqla.String)
    version_prefix = sqla.Column(sqla.String)
    excluded_versions = sqla.Column(sqla.PickleType)
    version_filters = sqla.Column(sqla.PickleType)


class SiteSettings(Base, FieldsMixin):
    __tablename__ = "site_settings"
    _FIELDS = """site_id name storage_prefix version_suffix
                 default_excluded_files default_excluded_versions
                 server_prefixes source_prefixes""".split()
    site_id = sqla.Column(sqla.String, nullable=False, primary_key=True)
    name = sqla.Column(sqla.String, nullable=False)
    storage_prefix = sqla.Column(sqla.String, nullable=False)
    version_suffix = sqla.Column(sqla.String, server_default="")
    default_excluded_files = sqla.Column(sqla.PickleType)
    default_excluded_versions = sqla.Column(sqla.PickleType)

    @hybrid_property
    def server_prefixes(self):
        mapped = {}
        for k, v in self._raw_server_prefixes.items():
            mapped[k] = v.local_prefix
        return mapped

    @server_prefixes.setter
    def server_prefixes(self, value):
        mapped = {}
        for k, v in value.items():
            mapped[k] = ServerPrefix.from_fields(self.site_id, k, v)
        self._raw_server_prefixes = mapped

    @hybrid_property
    def source_prefixes(self, key, prefixes):
        mapped = {}
        for k, v in self._raw_source_prefixes.items():
            mapped[k] = v.local_prefix
        return mapped

    @source_prefixes.setter
    def source_prefixes(self, value):
        mapped = {}
        for k, v in value.items():
            mapped[k] = SourcePrefix.from_fields(self.site_id, k, v)
        self._raw_source_prefixes = mapped


class ServerPrefix(Base, FieldsMixin):
    __tablename__ = "server_prefixes"
    _FIELDS = "site_id server_id local_prefix".split()
    site_id = sqla.Column(sqla.String, sqla.ForeignKey("site_settings.site_id"), primary_key=True)
    server_id = sqla.Column(sqla.String, sqla.ForeignKey("remote_servers.server_id"), primary_key=True)
    site = _linked_from(SiteSettings, "_raw_server_prefixes", "server_id")
    server = _linked_from(RemoteServer, "site_prefixes", "site_id")
    local_prefix = sqla.Column(sqla.String, nullable=False)


class SourcePrefix(Base, FieldsMixin):
    __tablename__ = "source_prefixes"
    _FIELDS = "site_id source_id local_prefix".split()
    site_id = sqla.Column(sqla.String, sqla.ForeignKey("site_settings.site_id"), primary_key=True)
    source_id = sqla.Column(sqla.String, sqla.ForeignKey("remote_sources.source_id"), primary_key=True)
    site = _linked_from(SiteSettings, "_raw_source_prefixes", "source_id")
    source = _linked_from(RemoteSource, "site_prefixes", "site_id")
    local_prefix = sqla.Column(sqla.String, nullable=False)


class LocalMirror(Base, FieldsMixin):
    __tablename__ = "local_mirrors"
    _FIELDS = """mirror_id tree_id site_id name description mirror_path
                 excluded_files sync_filters excluded_versions version_filters
                 enabled dry_run_only delete_old_dirs""".split()
    mirror_id = sqla.Column(sqla.String, primary_key=True)
    tree_id = sqla.Column(sqla.String, sqla.ForeignKey("remote_trees.tree_id"))
    source = relation(RemoteTree, backref=backref("mirrors", order_by=mirror_id))
    site_id = sqla.Column(sqla.String, sqla.ForeignKey("site_settings.site_id"))
    source = relation(SiteSettings, backref=backref("mirrors", order_by=mirror_id))
    name = sqla.Column(sqla.String)
    description = sqla.Column(sqla.String)
    mirror_path = sqla.Column(sqla.String)
    excluded_files = sqla.Column(sqla.PickleType)
    sync_filters = sqla.Column(sqla.PickleType)
    excluded_versions = sqla.Column(sqla.PickleType)
    version_filters = sqla.Column(sqla.PickleType)
    enabled = sqla.Column(sqla.Boolean, default=False)
    dry_run_only = sqla.Column(sqla.Boolean, default=False)
    delete_old_dirs = sqla.Column(sqla.Boolean, default=False)


def query_mirrors(session, mirrors=(), sources=(), servers=(), sites=()):
    """Build an SQLA query that filters for mirrors that match any of the
       supplied settings.
    """
    query = session.query(LocalMirror)
    filters = []
    for mirror in mirrors:
        filters.append(LocalMirror.mirror_id == mirror)
    for site in sites:
        filters.append(LocalMirror.site_id == site)
    if sources or servers:
        query = query.join(RemoteTree)
        query = query.join(RemoteSource)
        for source in sources:
            filters.append(RemoteSource.source_id == source)
        if servers:
            query = query.join(RemoteServer)
            for server in servers:
                filters.append(RemoteServer.server_id == server)
    if filters:
        if len(filters) == 1:
            qfilter = filters[0]
        else:
            qfilter = sqla.or_(*filters)
        query = query.filter(qfilter)
    return query


def in_memory_db():
    engine = sqla.create_engine("sqlite:///:memory:")
    site_db = Base.metadata
    site_db.create_all(engine)
    Session = sessionmaker(engine)
    session = Session()
    session.add_all(SyncType.from_fields(sync_type) for sync_type in SYNC_TYPES)
    session.commit()
    return Session
