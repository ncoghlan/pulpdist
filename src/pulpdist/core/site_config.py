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
from . import validation, site_sql

def check_mapping_sequence(spec):
    return validation.check_sequence(validation.check_mapping(spec))

class SiteConfig(validation.ValidatedConfig):
    """
    _SPEC = {
        u"LOCAL_SETTINGS": validation.check_mapping(LocalSettingsConfig),
        u"REMOTE_SETTINGS": validation.check_mapping(RemoteSettingsConfig),
        u"LOCAL_TREES": validation.check_mapping_sequence(LocalTreeConfig),
        u"REMOTE_TREES": validation.check_mapping_sequence(RemoteTreeConfig),
        u"REMOTE_SOURCES": validation.check_mapping_sequence(RemoteSourceConfig),
        u"REMOTE_SERVERS": validation.check_mapping_sequence(RemoteServerConfig),
        u"RAW_TREES": validation.check_mapping_sequence(RemoteTreeConfig),
    }
    """

    def __init__(self, *args, **kwds):
        super(SiteConfig, self).__init__(*args, **kwds)
        self._db_session_factory = site_sql.in_memory_db()

    @property
    def repo_config(self):
        if self._repo_config is None:
            self.validate()
        return self._repo_config

    def get_db_session(self):
        return self._db_session_factory()

    def _populate_db(self):
        db_session = self.get_db_session()
        # Populate with data

    def make_repo_config(self):
        self._populate_db()
        db_session = self.get_db_session()
        # Query populated DB

    def validate(self):
        super(SiteConfig, self).validate()
        repo_config = self.make_repo_config()
        repo_config.validate()
        self._repo_config = repo_config

