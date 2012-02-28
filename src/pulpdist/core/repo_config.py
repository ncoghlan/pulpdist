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
from . import sync_config, validation

_fail_validation = validation.fail_validation

class RepoConfig(validation.ValidatedConfig):
    _SPEC = {
        u"repo_id": validation.check_simple_id(),
        u"display_name": validation.check_text(),
        u"description": validation.check_text(allow_none=True),
        u"notes": validation.check_type(dict, allow_none=True),
        u"importer_type_id": validation.check_pulp_id(allow_none=True),
        u"importer_config": validation.check_type(dict, allow_none=True),
    }
    _DEFAULTS = {
        u"description": None,
        u"notes": None,
        u"importer_type_id": None,
        u"importer_config": None,
    }

    _IMPORTER_CONFIGS = {
        u"simple_tree": sync_config.TreeSyncConfig,
        u"versioned_tree": sync_config.VersionedSyncConfig,
        u"snapshot_tree": sync_config.SnapshotSyncConfig,
    }

    def __init__(self, config):
        super(RepoConfig, self).__init__(config)

    def validate(self):
        super(RepoConfig, self).validate()
        config = self.config
        importer_id = config["importer_type_id"]
        importer_config = config["importer_config"]
        if importer_id is None:
            if importer_config is not None:
                _fail_validation("Importer config set without importer type id")
            return
        if importer_config is None:
            _fail_validation("Importer type id set without importer config")
        try:
            config_type = self._IMPORTER_CONFIGS[importer_id]
        except KeyError:
            _fail_validation("Unknown importer type '{0}'", importer_id)
        config_type(importer_config).validate()

