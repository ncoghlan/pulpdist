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

from . import test_sync_trees
from .compat import unittest
from .. import site_config, site_sql, validation, sync_trees

# The tests in this file revolve around the carefully crafted TEST_CONFIG
# definition. It's designed to exercise most of the interest flows through
# the validation and conversion code, as well as to be compatible with the
# tree layouts expected by example_trees.TreeTestCase.

# Individual tests can then tweak the known valid config to induce
# expected failures and perform any other desired checks.

class TestSiteConfig(unittest.TestCase):

    def test_db_session(self):
        # Quick sanity check on setting up the DB schema
        config = site_config.SiteConfig()
        config._init_db()
        session = config._get_db_session()
        mirrors = list(session.query(site_sql.LocalMirror))
        self.assertEqual(mirrors, [])

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

    def test_remote_no_version_pattern(self):
        example = json.loads(TEST_CONFIG)
        example["REMOTE_TREES"][1]["version_pattern"] = None
        example["REMOTE_TREES"][1]["version_prefix"] = None
        site = site_config.SiteConfig(example)
        self.assertSpecInvalid(site)

    def test_remote_version_pattern_conflict(self):
        example = json.loads(TEST_CONFIG)
        example["REMOTE_TREES"][1]["version_pattern"] = "set"
        example["REMOTE_TREES"][1]["version_prefix"] = "set"
        site = site_config.SiteConfig(example)
        self.assertSpecInvalid(site)


class TestQueryMirrors(unittest.TestCase):

    def setUp(self):
        self.config = config = json.loads(TEST_CONFIG)
        self.site = site = site_config.SiteConfig(config)

    def _get_mirrors(self, *args, **kwds):
        return sorted(m.mirror_id for m in self.site.query_mirrors(*args, **kwds))

    def test_simple_query(self):
        self.assertEqual(self._get_mirrors(), ALL_MIRRORS)

    def test_query_by_mirror_id(self):
        mirrors = self._get_mirrors(DEFAULT_MIRRORS)
        self.assertEqual(mirrors, DEFAULT_MIRRORS)

    def test_query_by_source_id(self):
        mirrors = self._get_mirrors(sources=[DEFAULT_SOURCE])
        self.assertEqual(mirrors, DEFAULT_MIRRORS)

    def test_query_by_server_id(self):
        mirrors = self._get_mirrors(servers=[DEFAULT_SERVER])
        self.assertEqual(mirrors, DEFAULT_MIRRORS)

    def test_query_by_site_id(self):
        mirrors = self._get_mirrors(sites=[DEFAULT_SITE])
        self.assertEqual(mirrors, DEFAULT_MIRRORS)

    def test_query_combined(self):
        mirrors = self._get_mirrors(OTHER_MIRRORS, sites=[DEFAULT_SITE])
        self.assertEqual(mirrors, ALL_MIRRORS)


class TestConversion(unittest.TestCase):

    def setUp(self):
        self.config = config = json.loads(TEST_CONFIG)
        self.site = site = site_config.SiteConfig(config)
        self.expected = json.loads(EXPECTED_REPO_CONFIGS)

    # Ideally this would be broken up into finer grained unit tests
    # but at least this will pick up if anything major goes wrong in
    # the converter, even if it doesn't make it all that easy to debug
    # the fault
    def test_make_repo_configs(self):
        repo_configs = self.site.make_repo_configs()
        self.assertEqual(repo_configs, self.expected)

class TestDataTransfer(test_sync_trees.BaseTestCase):

    def setUp(self):
        super(TestDataTransfer, self).setUp()
        self.config = config = json.loads(TEST_CONFIG)
        for site in config["SITE_SETTINGS"]:
            site["storage_prefix"] = self.local_path
        for server in config["REMOTE_SERVERS"]:
            server["rsync_port"] = self.rsyncd.port
        for mirror in config["LOCAL_MIRRORS"]:
            mirror["enabled"] = True
        self.site = site_config.SiteConfig(config)

    def test_simple_tree(self):
        repo = self.site.make_repo_configs(mirrors=["simple_sync"])[0]
        params = repo["importer_config"]
        local_path = params["local_path"]
        task = sync_trees.SyncTree(params)
        stats = dict(self.EXPECTED_TREE_STATS)
        self.check_sync_details(task.run_sync(), "SYNC_COMPLETED", stats)
        self.check_tree_layout(local_path)
        stats.update(self.EXPECTED_REPEAT_STATS)
        self.check_sync_details(task.run_sync(), "SYNC_UP_TO_DATE", stats)
        self.check_tree_layout(local_path)

    def test_versioned_tree(self):
        raise NotImplementedError

    def test_snapshot_tree(self):
        raise NotImplementedError

    def test_raw_tree(self):
        raise NotImplementedError


DEFAULT_SITE = "default"
DEFAULT_SERVER = "demo_server"
DEFAULT_SOURCE = "sync_demo"

DEFAULT_MIRRORS = ["simple_sync", "snapshot_sync"]
OTHER_MIRRORS = ["versioned_sync"]

ALL_MIRRORS = sorted(DEFAULT_MIRRORS + OTHER_MIRRORS)


TEST_CONFIG = """\
{
  "SITE_SETTINGS": [
    {
      "site_id": "default",
      "name": "Default Site",
      "storage_prefix": "/var/www/pub",
      "server_prefixes": {
        "demo_server": "sync_demo",
        "other_demo_server": "sync_demo/sync_demo_trees"
      },
      "source_prefixes": {
        "sync_demo": "sync_demo_trees"
      },
      "version_suffix": "*",
      "default_excluded_files": ["*dull*"]
    },
    {
      "site_id": "other",
      "name": "Other Site",
      "storage_prefix": "/var/www/pub",
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
      "site_id": "other",
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
      "source_id": "sync_demo_other",
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
      "remote_path": "test_data"
    },
    {
      "source_id": "sync_demo_other",
      "server_id": "other_demo_server",
      "name": "Other Sync Demo Trees",
      "remote_path": "test_data"
    }
  ],
  "REMOTE_SERVERS": [
    {
      "server_id": "demo_server",
      "name": "Sync Demo Server",
      "dns": "localhost"
    },
    {
      "server_id": "other_demo_server",
      "name": "Other Sync Demo Server",
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

EXPECTED_REPO_CONFIGS = """\
[
  {
    "repo_id": "simple_sync",
    "display_name": "Simple Sync Demo",
    "description": "Demonstration of the simple tree sync plugin",
    "notes": {
      "pulpdist": {
        "source_id": "simple_sync",
        "server_id": "demo_server",
        "sync_hours": 0,
        "site_id": "default",
        "tree_id": "simple_sync"
      },
      "site_custom": {
        "origin": "PulpDist example repository"
      },
      "basic": "note"
    },
    "importer_type_id": "simple_tree",
    "importer_config": {
      "sync_filters": [
        "exclude_irrelevant/"
      ],
      "local_path": "/var/www/pub/sync_demo/sync_demo_trees/simple/",
      "remote_server": "localhost",
      "dry_run_only": false,
      "old_remote_daemon": false,
      "tree_name": "simple_sync",
      "excluded_files": [
        "*skip*",
        "*dull*"
      ],
      "enabled": false,
      "remote_path": "/test_data/simple/"
    }
  },
  {
    "repo_id": "versioned_sync",
    "display_name": "Versioned Sync Demo",
    "description": "Demonstration of the versioned tree sync plugin",
    "notes": {
      "pulpdist": {
        "source_id": "versioned_sync",
        "server_id": "other_demo_server",
        "sync_hours": 12,
        "site_id": "other",
        "tree_id": "versioned_sync"
      },
      "site_custom": {
        "origin": "PulpDist example repository"
      }
    },
    "importer_type_id": "versioned_tree",
    "importer_config": {
      "sync_filters": [
        "exclude_dull/",
        "exclude_irrelevant/"
      ],
      "dry_run_only": false,
      "subdir_filters": [],
      "remote_path": "/test_data/versioned/",
      "excluded_versions": [],
      "old_remote_daemon": false,
      "tree_name": "versioned_sync",
      "excluded_files": [
        "*skip*",
        "*dull*"
      ],
      "remote_server": "localhost",
      "version_pattern": "relevant*",
      "enabled": false,
      "delete_old_dirs": false,
      "local_path": "/var/www/pub/sync_demo/sync_demo_trees/versioned/"
    }
  },
  {
    "repo_id": "snapshot_sync",
    "display_name": "Snapshot Sync Demo",
    "description": "Demonstration of the snapshot tree sync plugin",
    "notes": {
      "pulpdist": {
        "source_id": "snapshot_sync",
        "server_id": "demo_server",
        "sync_hours": 1,
        "site_id": "default",
        "tree_id": "snapshot_sync"
      },
      "site_custom": {
        "origin": "PulpDist example repository"
      }
    },
    "importer_type_id": "snapshot_tree",
    "importer_config": {
      "sync_filters": [
        "exclude_irrelevant/",
        "exclude_dull/"
      ],
      "dry_run_only": false,
      "subdir_filters": [],
      "remote_path": "/test_data/snapshot/",
      "excluded_versions": [],
      "latest_link_name": "latest-relev",
      "old_remote_daemon": false,
      "tree_name": "snapshot_sync",
      "excluded_files": [
        "*skip*",
        "*dull*"
      ],
      "remote_server": "localhost",
      "version_pattern": "relev*",
      "enabled": false,
      "delete_old_dirs": false,
      "local_path": "/var/www/pub/sync_demo/sync_demo_trees/snapshot/"
    }
  },
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
      "sync_filters": [
        "exclude_irrelevant/",
        "exclude_dull/"
      ],
      "remote_server": "localhost",
      "remote_path": "/demo/simple/",
      "local_path": "/var/www/pub/sync_demo_raw/",
      "tree_name": "Raw Simple Tree",
      "excluded_files": [
        "*skip*"
      ]
    }
  }
]
"""

if __name__ == '__main__':
    unittest.main()