#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
"""Basic test suite for sync transfer operations"""

import json

from .compat import unittest
from .. import site_config, site_sql, validation

class TestSiteConfig(unittest.TestCase):

    def test_db_session(self):
        # Quick sanity check on setting up the DB schema
        config = site_config.SiteConfig()
        config._init_db()
        session = config._get_db_session()
        sync_types = session.query(site_sql.SyncType).order_by('sync_type')
        self.assertEqual([r.sync_type for r in sync_types], sorted(site_sql.SYNC_TYPES))

    def assertSpecValid(self, config):
        # Checks that the document validation passes
        try:
            config._validate_spec()
        except validation.ValidationError as exc:
            self.fail(exc)

    def assertSpecInvalid(self, config):
        # Checks that an error is picked up by the document validation
        self.assertRaises(validation.ValidationError, config._validate_spec)

    def assertValid(self, config):
        # Checks that both document and cross-reference validation pass
        try:
            config.validate()
        except validation.ValidationError as exc:
            self.fail(exc)

    def assertInvalid(self, config):
        # Checks that either document or cross reference validation fails
        self.assertRaises(validation.ValidationError, config.validate)

    def test_read_config(self):
        # This checks that the initial validation of the config file works
        example = json.loads(TEST_CONFIG)
        self.assertSpecValid(site_config.SiteConfig(example))

    def test_validate_config(self):
        # And this checks the cross-references validate
        example = json.loads(TEST_CONFIG)
        self.assertValid(site_config.SiteConfig(example))

    def test_missing_top_level_entries(self):
        base_config = json.loads(TEST_CONFIG)
        for entry in base_config.keys():
            example = base_config.copy()
            example.pop(entry)
            site = site_config.SiteConfig(example)
            self.assertSpecInvalid(site)
            self.assertInvalid(site)

    def test_server_prefix_bad_path(self):
        example = json.loads(TEST_CONFIG)
        example["SITE_SETTINGS"][0]["server_prefixes"]["demo_server"] = "*"
        site = site_config.SiteConfig(example)
        self.assertSpecInvalid(site)
        self.assertInvalid(site)

    def test_server_prefix_missing_server(self):
        example = json.loads(TEST_CONFIG)
        example["SITE_SETTINGS"][0]["server_prefixes"]["missing"] = "path"
        site = site_config.SiteConfig(example)
        self.assertSpecValid(site)
        self.assertInvalid(site)

    def test_source_prefix_bad_path(self):
        example = json.loads(TEST_CONFIG)
        example["SITE_SETTINGS"][0]["source_prefixes"]["demo_server"] = "*"
        site = site_config.SiteConfig(example)
        self.assertSpecInvalid(site)
        self.assertInvalid(site)

    def test_source_prefix_missing_source(self):
        example = json.loads(TEST_CONFIG)
        example["SITE_SETTINGS"][0]["source_prefixes"]["missing"] = "path"
        site = site_config.SiteConfig(example)
        self.assertSpecValid(site)
        self.assertInvalid(site)

    def test_local_mirror_missing_site(self):
        example = json.loads(TEST_CONFIG)
        example["LOCAL_MIRRORS"][0]["site_id"] = "missing"
        site = site_config.SiteConfig(example)
        self.assertSpecValid(site)
        self.assertInvalid(site)

    def test_local_mirror_missing_tree(self):
        example = json.loads(TEST_CONFIG)
        example["LOCAL_MIRRORS"][0]["tree_id"] = "missing"
        site = site_config.SiteConfig(example)
        self.assertSpecValid(site)
        self.assertInvalid(site)

    def test_remote_tree_missing_source(self):
        example = json.loads(TEST_CONFIG)
        example["REMOTE_TREES"][0]["source_id"] = "missing"
        site = site_config.SiteConfig(example)
        self.assertSpecValid(site)
        self.assertInvalid(site)

    def test_remote_source_missing_server(self):
        example = json.loads(TEST_CONFIG)
        example["REMOTE_SOURCES"][0]["server_id"] = "missing"
        site = site_config.SiteConfig(example)
        self.assertSpecValid(site)
        self.assertInvalid(site)

TEST_CONFIG = """\
{
  "SITE_SETTINGS": [
    {
      "site_id": "default",
      "name": "Default Site",
      "storage_prefix": "/var/www/pub",
      "server_prefixes": {
        "demo_server": "sync_demo"
      },
      "source_prefixes": {
        "sync_demo": "sync_demo_trees"
      },
      "version_suffix": "*"
    }
  ],
  "LOCAL_MIRRORS": [
    {
      "mirror_id": "simple_sync",
      "tree_id": "simple_sync",
      "excluded_files": ["*skip*"],
      "sync_filters": ["exclude_irrelevant/"],
      "notes": {
        "basic": "note",
        "site_custom": {
          "origin": "PulpDist example repository"
        }
      }
    },
    {
      "mirror_id": "versioned_sync",
      "tree_id": "versioned_sync",
      "sync_filters": ["exclude_dull/"],
      "excluded_versions": ["relevant-but*"],
      "notes": {
        "site_custom": {
          "origin": "PulpDist example repository"
        }
      }
    },
    {
      "mirror_id": "snapshot_sync",
      "tree_id": "snapshot_sync",
      "notes": {
        "site_custom": {
          "origin": "PulpDist example repository"
        }
      }
    }
  ],
  "REMOTE_TREES": [
    {
      "tree_id": "simple_sync",
      "name": "Simple Sync Demo",
      "description": "Demonstration of the simple tree sync plugin",
      "tree_path": "simple",
      "sync_type": "simple",
      "sync_hours": 0,
      "source_id": "sync_demo"
    },
    {
      "tree_id": "versioned_sync",
      "name": "Versioned Sync Demo",
      "description": "Demonstration of the versioned tree sync plugin",
      "tree_path": "versioned",
      "sync_type": "versioned",
      "sync_hours": 12,
      "source_id": "sync_demo",
      "version_pattern": "relevant*",
      "excluded_files": ["*skip*"],
      "sync_filters": ["exclude_irrelevant/"]
    },
    {
      "tree_id": "snapshot_sync",
      "name": "Snapshot Sync Demo",
      "description": "Demonstration of the snapshot tree sync plugin",
      "tree_path": "snapshot",
      "sync_type": "snapshot",
      "sync_hours": 1,
      "source_id": "sync_demo",
      "version_prefix": "relev",
      "excluded_versions": ["relevant-but*"],
      "excluded_files": ["*skip*"],
      "sync_filters": ["exclude_irrelevant/", "exclude_dull/"]
    }
  ],
  "REMOTE_SOURCES": [
    {
      "source_id": "sync_demo",
      "server_id": "demo_server",
      "name": "Sync Demo Trees",
      "remote_path": "demo"
    }
  ],
  "REMOTE_SERVERS": [
    {
      "server_id": "demo_server",
      "name": "Sync Demo Server",
      "dns": "localhost"
    }
  ],
  "RAW_TREES": [
    {
      "repo_id": "raw_sync",
      "display_name": "Raw Sync Demo",
      "description": "Demonstration of raw sync configuration in site config",
      "notes": {
        "pulpdist": {
          "sync_hours": 24
        },
        "site_custom": {
          "origin": "PulpDist example repository"
        }
      },
      "importer_type_id": "simple_tree",
      "importer_config": {
        "tree_name": "Raw Simple Tree",
        "remote_server": "localhost",
        "remote_path": "/demo/simple/",
        "local_path": "/var/www/pub/sync_demo_raw/",
        "excluded_files": ["*skip*"],
        "sync_filters": ["exclude_irrelevant/", "exclude_dull/"]
      }
    }
  ]
}
"""

if __name__ == '__main__':
    unittest.main()
