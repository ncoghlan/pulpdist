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

"""Site definition for use in testing"""
from .. import site_config

def get_site_config():
    return site_config.SiteConfig.from_json(TEST_CONFIG)

# Tests that require site detaisl revolve around the carefully crafted
# TEST_CONFIG definition. It's designed to exercise most of the interesting
# flows through the validation and conversion code, as well as to be compatible
# with the tree layouts expected by example_trees.TreeTestCase.

# Individual tests can then tweak the known valid config to induce
# expected failures and perform any other desired checks.

DEFAULT_SITE = "default"
DEFAULT_SERVER = "demo_server"
DEFAULT_SOURCE = "sync_demo"
DEFAULT_TREES = ["simple_sync", "snapshot_sync"]

DEFAULT_MIRRORS = DEFAULT_TREES[:]
OTHER_MIRRORS = ["versioned_sync"]

ALL_MIRRORS = sorted(DEFAULT_MIRRORS + OTHER_MIRRORS)

DEFAULT_REPOS = ["simple_sync__default", "snapshot_sync__default"]
OTHER_REPOS = ["versioned_sync__other", "raw_sync"]

ALL_REPOS = sorted(DEFAULT_REPOS + OTHER_REPOS)

IMPORTER_TYPES = {
    "raw_sync": "simple_tree",
    "simple_sync__default": "simple_tree",
    "snapshot_sync__default": "snapshot_tree",
    "versioned_sync__other": "versioned_tree",
}

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
      "excluded_files": ["*skip*"],
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
        "remote_path": "/test_data/simple/",
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
    "repo_id": "simple_sync__default",
    "display_name": "Simple Sync Demo",
    "description": "Demonstration of the simple tree sync plugin",
    "notes": {
      "pulpdist": {
        "mirror_id": "simple_sync",
        "source_id": "sync_demo",
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
      "tree_name": "simple_sync__default",
      "excluded_files": [
        "*skip*",
        "*dull*"
      ],
      "enabled": false,
      "remote_path": "/test_data/simple/"
    }
  },
  {
    "repo_id": "versioned_sync__other",
    "display_name": "Versioned Sync Demo",
    "description": "Demonstration of the versioned tree sync plugin",
    "notes": {
      "pulpdist": {
        "mirror_id": "versioned_sync",
        "source_id": "sync_demo_other",
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
      "excluded_versions": ["relevant-but*"],
      "old_remote_daemon": false,
      "tree_name": "versioned_sync__other",
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
    "repo_id": "snapshot_sync__default",
    "display_name": "Snapshot Sync Demo",
    "description": "Demonstration of the snapshot tree sync plugin",
    "notes": {
      "pulpdist": {
        "mirror_id": "snapshot_sync",
        "source_id": "sync_demo",
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
      "excluded_versions": ["relevant-but*"],
      "latest_link_name": "latest-relev",
      "old_remote_daemon": false,
      "tree_name": "snapshot_sync__default",
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
      "remote_path": "/test_data/simple/",
      "local_path": "/var/www/pub/sync_demo_raw/",
      "tree_name": "Raw Simple Tree",
      "excluded_files": [
        "*skip*"
      ]
    }
  }
]
"""
