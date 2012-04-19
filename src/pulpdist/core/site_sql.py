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
from sqlalchemy.orm import sessionmaker, relation, backref
from sqlalchemy.orm.collections import attribute_mapped_collection

from . import util

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
    _FIELDS = "source_id server_id name remote_path listing_suffix".split()
    source_id = sqla.Column(sqla.String, primary_key=True)
    server_id = sqla.Column(sqla.String, sqla.ForeignKey("remote_servers.server_id"))
    server = _linked_from(RemoteServer, "sources", "source_id")
    name = sqla.Column(sqla.String, nullable=False)
    remote_path = sqla.Column(sqla.String, nullable=False)
    listing_suffix = sqla.Column(sqla.String, server_default="")


class RemoteTree(Base, FieldsMixin):
    __tablename__ = "remote_trees"
    _FIELDS = """tree_id source_id name description tree_path sync_hours
                 sync_type exclude_from_sync sync_filters
                 listing_pattern listing_prefix latest_link
                 exclude_from_listing listing_filters""".split()
    tree_id = sqla.Column(sqla.String, primary_key=True)
    source_id = sqla.Column(sqla.String, sqla.ForeignKey("remote_sources.source_id"))
    source = _linked_from(RemoteSource, "trees", "tree_id")
    name = sqla.Column(sqla.String, nullable=False)
    description = sqla.Column(sqla.String, server_default="")
    tree_path = sqla.Column(sqla.String, nullable=False)
    sync_hours = sqla.Column(sqla.Integer)
    sync_type = sqla.Column(sqla.String)
    exclude_from_sync = sqla.Column(sqla.PickleType)
    sync_filters = sqla.Column(sqla.PickleType)
    listing_pattern = sqla.Column(sqla.String)
    listing_prefix = sqla.Column(sqla.String)
    latest_link = sqla.Column(sqla.String)
    exclude_from_listing = sqla.Column(sqla.PickleType)
    listing_filters = sqla.Column(sqla.PickleType)


class SiteSettings(Base, FieldsMixin):
    __tablename__ = "site_settings"
    _FIELDS = """site_id name storage_prefix
                 exclude_from_sync exclude_from_listing
                 server_prefixes source_prefixes""".split()
    site_id = sqla.Column(sqla.String, nullable=False, primary_key=True)
    name = sqla.Column(sqla.String, nullable=False)
    storage_prefix = sqla.Column(sqla.String, nullable=False)
    exclude_from_sync = sqla.Column(sqla.PickleType)
    exclude_from_listing = sqla.Column(sqla.PickleType)

    @property
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

    @property
    def source_prefixes(self):
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
                 exclude_from_sync sync_filters
                 exclude_from_listing listing_filters
                 notes enabled dry_run_only
                 delete_old_dirs sync_latest_only""".split()
    mirror_id = sqla.Column(sqla.String, primary_key=True)
    tree_id = sqla.Column(sqla.String, sqla.ForeignKey("remote_trees.tree_id"))
    tree = relation(RemoteTree, backref=backref("mirrors", order_by=mirror_id))
    site_id = sqla.Column(sqla.String, sqla.ForeignKey("site_settings.site_id"),
                          primary_key=True)
    site = relation(SiteSettings, backref=backref("mirrors", order_by=mirror_id),
                    primaryjoin = SiteSettings.site_id == site_id)
    name = sqla.Column(sqla.String)
    description = sqla.Column(sqla.String)
    mirror_path = sqla.Column(sqla.String)
    exclude_from_sync = sqla.Column(sqla.PickleType)
    sync_filters = sqla.Column(sqla.PickleType)
    exclude_from_listing = sqla.Column(sqla.PickleType)
    listing_filters = sqla.Column(sqla.PickleType)
    notes = sqla.Column(sqla.PickleType)
    enabled = sqla.Column(sqla.Boolean, default=False)
    dry_run_only = sqla.Column(sqla.Boolean, default=False)
    delete_old_dirs = sqla.Column(sqla.Boolean, default=False)
    sync_latest_only = sqla.Column(sqla.Boolean, default=False)

    # Easy access to the default site for creation of the repo definition
    default_site_id = sqla.Column(sqla.String,
                                  sqla.ForeignKey("site_settings.site_id"),
                                  default="default")
    default_site = relation(SiteSettings, viewonly = True,
                            primaryjoin = SiteSettings.site_id == default_site_id)


class PulpRepository(Base, FieldsMixin):
    __tablename__ = "pulp_repositories"
    __table_args__ = (
        sqla.ForeignKeyConstraint("mirror_id site_id".split(),
                                 (LocalMirror.mirror_id, LocalMirror.site_id)),
        {}
    )
    _FIELDS = """repo_id mirror_id site_id tree_id source_id
                 server_id sync_hours config""".split()
    repo_id = sqla.Column(sqla.String, primary_key=True)
    mirror_id = sqla.Column(sqla.String)
    site_id = sqla.Column(sqla.String)
    tree_id = sqla.Column(sqla.String, sqla.ForeignKey("remote_trees.tree_id"))
    source_id = sqla.Column(sqla.String, sqla.ForeignKey("remote_sources.source_id"))
    server_id = sqla.Column(sqla.String, sqla.ForeignKey("remote_servers.server_id"))
    sync_hours = sqla.Column(sqla.Integer)
    config = sqla.Column(sqla.PickleType)


def query_mirrors(session, mirrors=(), trees=(), sources=(), servers=(), sites=()):
    """Build an SQLA query that filters for mirrors that match any of the
       supplied settings.
    """
    query = session.query(LocalMirror)
    filters = []
    for mirror in mirrors:
        filters.append(LocalMirror.mirror_id == mirror)
    for tree in trees:
        filters.append(LocalMirror.tree_id == tree)
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


def query_repos(session, repos=(), mirrors=(), trees=(), sources=(), servers=(), sites=()):
    """Build an SQLA query that filters for mirrors that match any of the
       supplied settings.
    """
    query = session.query(PulpRepository)
    filters = []
    for repo in repos:
        filters.append(PulpRepository.repo_id == repo)
    for mirror in mirrors:
        filters.append(PulpRepository.mirror_id == mirror)
    for tree in trees:
        filters.append(PulpRepository.tree_id == tree)
    for site in sites:
        filters.append(PulpRepository.site_id == site)
    for source in sources:
        filters.append(PulpRepository.source_id == source)
    for server in servers:
        filters.append(PulpRepository.server_id == server)
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
    def _get_session():
        db_session = Session()
        db_session.execute('pragma foreign_keys=on')
        return db_session
    return _get_session
