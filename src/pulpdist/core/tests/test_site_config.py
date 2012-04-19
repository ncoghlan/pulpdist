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
"""Basic test suite for site configuration"""

import json

from . import test_sync_trees
from .. import site_config, site_sql, validation, sync_trees, mirror_config
from .compat import unittest

from . import example_site
# Quick fix after moving the example site definition out to a separate file...
from .example_site import *

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

    def test_empty_config(self):
        config = site_config.SiteConfig()
        self.assertSpecValid(config)
        self.assertValid(config)

    def test_read_config(self):
        # This checks that the initial validation of the config file works
        example = json.loads(TEST_CONFIG)
        self.assertSpecValid(site_config.SiteConfig(example))

    def test_get_site_config(self):
        # This checks a helper function in example_site
        example = example_site.get_site_config()
        self.assertSpecValid(example)
        self.assertValid(example)

    def test_raw_trees_only(self):
        example = json.loads(TEST_CONFIG)
        raw_trees = {u"RAW_TREES": example["RAW_TREES"]}
        config = site_config.SiteConfig()
        self.assertSpecValid(config)
        self.assertValid(config)

    def test_validate_config(self):
        # And this checks the cross-references validate
        example = json.loads(TEST_CONFIG)
        self.assertValid(site_config.SiteConfig(example))

    def test_missing_top_level_entries(self):
        base_config = json.loads(TEST_CONFIG)
        _missing_ok = "LOCAL_MIRRORS RAW_TREES".split()
        for entry in base_config.keys():
            example = base_config.copy()
            example.pop(entry)
            site = site_config.SiteConfig(example)
            self.assertSpecValid(site)
            if entry in _missing_ok:
                self.assertValid(site)
            else:
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

    def test_server_prefix_null_server(self):
        example = json.loads(TEST_CONFIG)
        example["SITE_SETTINGS"][0]["server_prefixes"][None] = "path"
        site = site_config.SiteConfig(example)
        self.assertSpecInvalid(site)

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

    def test_source_prefix_null_source(self):
        example = json.loads(TEST_CONFIG)
        example["SITE_SETTINGS"][0]["source_prefixes"][None] = "path"
        site = site_config.SiteConfig(example)
        self.assertSpecInvalid(site)

    def _check_missing_ref(self, kind, id_attr):
        example = json.loads(TEST_CONFIG)
        example[kind][0][id_attr] = "missing"
        site = site_config.SiteConfig(example)
        self.assertSpecValid(site)
        self.assertInvalid(site)

    def test_local_mirror_missing_site(self):
        self._check_missing_ref("LOCAL_MIRRORS", "site_id")

    def test_local_mirror_missing_tree(self):
        self._check_missing_ref("LOCAL_MIRRORS", "tree_id")

    def test_remote_tree_missing_source(self):
        self._check_missing_ref("REMOTE_TREES", "source_id")

    def test_remote_source_missing_server(self):
        self._check_missing_ref("REMOTE_SOURCES", "server_id")

    def _check_null_ref(self, kind, id_attr):
        example = json.loads(TEST_CONFIG)
        example[kind][0][id_attr] = None
        site = site_config.SiteConfig(example)
        self.assertSpecInvalid(site)

    def test_local_mirror_null_site(self):
        self._check_null_ref("LOCAL_MIRRORS", "site_id")

    def test_local_mirror_null_tree(self):
        self._check_null_ref("LOCAL_MIRRORS", "tree_id")

    def test_remote_tree_null_source(self):
        self._check_null_ref("REMOTE_TREES", "source_id")

    def test_remote_source_null_server(self):
        self._check_null_ref("REMOTE_SOURCES", "server_id")

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

    def _check_duplicate_id(self, kind):
        example = json.loads(TEST_CONFIG)
        example[kind].append(example[kind][0])
        site = site_config.SiteConfig(example)
        self.assertSpecValid(site)
        self.assertInvalid(site)

    def test_duplicate_site_id(self):
        self._check_duplicate_id("SITE_SETTINGS")

    def test_duplicate_server_id(self):
        self._check_duplicate_id("REMOTE_SERVERS")

    def test_duplicate_source_id(self):
        self._check_duplicate_id("REMOTE_SOURCES")

    def test_duplicate_tree_id(self):
        self._check_duplicate_id("REMOTE_TREES")

    def test_duplicate_mirror_id(self):
        self._check_duplicate_id("LOCAL_MIRRORS")

    def test_duplicate_mirror_id_distinct_sites(self):
        example = json.loads(TEST_CONFIG)
        mirrors = example["LOCAL_MIRRORS"]
        new_mirror = mirrors[0].copy()
        new_mirror["site_id"] = "other"
        mirrors.append(new_mirror)
        site = site_config.SiteConfig(example)
        self.assertSpecValid(site)
        self.assertValid(site)

    def test_duplicate_repo_id(self):
        self._check_duplicate_id("RAW_TREES")

    def test_mirror_repo_id_conflict(self):
        example = json.loads(TEST_CONFIG)
        mirror_config = example["LOCAL_MIRRORS"][0]
        mirror_id = mirror_config["mirror_id"]
        site_id = mirror_config.get("site_id", "default")
        repo_id = "{0}__{1}".format(mirror_id, site_id)
        example["RAW_TREES"][0]["repo_id"] = repo_id
        site = site_config.SiteConfig(example)
        self.assertSpecValid(site)
        self.assertInvalid(site)

    # BZ#806740, handle latest link naming variants
    def test_latest_link(self):
        config = json.loads(TEST_CONFIG)
        expected = config["REMOTE_TREES"][2]["latest_link"]
        site = site_config.SiteConfig(config)
        repos = site.get_repo_configs(mirrors=["snapshot_sync"])
        self.assertEqual(len(repos), 1)
        importer = repos[0]["importer_config"]
        self.assertEqual(importer["latest_link_name"], expected)

    def test_no_latest_link(self):
        config = json.loads(TEST_CONFIG)
        del config["REMOTE_TREES"][2]["latest_link"]
        site = site_config.SiteConfig(config)
        repos = site.get_repo_configs(mirrors=["snapshot_sync"])
        self.assertEqual(len(repos), 1)
        importer = repos[0]["importer_config"]
        self.assertNotIn("latest_link_name", importer)

    def test_omit_latest_link(self):
        config = json.loads(TEST_CONFIG)
        config["REMOTE_TREES"][2]["latest_link"] = None
        site = site_config.SiteConfig(config)
        repos = site.get_repo_configs(mirrors=["snapshot_sync"])
        self.assertEqual(len(repos), 1)
        importer = repos[0]["importer_config"]
        self.assertNotIn("latest_link_name", importer)

    # BZ#813667, handle syncing only the latest snapshot tree
    def test_sync_latest_only(self):
        config = json.loads(TEST_CONFIG)
        config["LOCAL_MIRRORS"][2]["sync_latest_only"] = True
        site = site_config.SiteConfig(config)
        repos = site.get_repo_configs(mirrors=["snapshot_sync"])
        self.assertEqual(len(repos), 1)
        importer = repos[0]["importer_config"]
        self.assertTrue(importer["sync_latest_only"])


class TestQueryMirrors(unittest.TestCase):

    def setUp(self):
        self.config = config = json.loads(TEST_CONFIG)
        self.site = site = site_config.SiteConfig(config)

    def _get_mirrors(self, *args, **kwds):
        return sorted(m.mirror_id for m in self.site.query_mirrors(*args, **kwds))

    def test_simple_query(self):
        self.assertEqual(self._get_mirrors(), ALL_MIRRORS)

    def test_query_by_mirror_id(self):
        mirrors = self._get_mirrors(mirrors=DEFAULT_MIRRORS)
        self.assertEqual(mirrors, DEFAULT_MIRRORS)

    def test_query_by_tree_id(self):
        mirrors = self._get_mirrors(trees=DEFAULT_TREES)
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
        mirrors = self._get_mirrors(mirrors=OTHER_MIRRORS, sites=[DEFAULT_SITE])
        self.assertEqual(mirrors, ALL_MIRRORS)


class TestQueryRepos(TestQueryMirrors):
    def _get_mirrors(self, *args, **kwds):
        return sorted(r.mirror_id for r in self.site.query_repos(*args, **kwds))

    def _get_repos(self, *args, **kwds):
        return sorted(r.repo_id for r in self.site.query_repos(*args, **kwds))

    def test_simple_query(self):
        self.assertEqual(self._get_repos(), ALL_REPOS)

    def test_query_by_repo_id(self):
        repos = self._get_repos(repos=DEFAULT_REPOS)
        self.assertEqual(repos, DEFAULT_REPOS)


class TestConversion(unittest.TestCase):

    def setUp(self):
        self.config = config = json.loads(TEST_CONFIG)
        self.site = site = site_config.SiteConfig(config)
        expected_seq = json.loads(EXPECTED_REPO_CONFIGS)
        expected = {}
        for repo in expected_seq:
            repo_id = repo["repo_id"]
            expected[repo_id] = repo
        self.expected = expected

    # Ideally this would be broken up into finer grained unit tests
    # but at least this will pick up if anything major goes wrong in
    # the converter, even if it doesn't make it all that easy to debug
    # the fault
    def test_get_repo_configs(self):
        repo_configs = self.site.get_repo_configs()
        expected = self.expected
        self.assertEqual(len(repo_configs), len(expected))
        self.maxDiff = None
        for repo in repo_configs:
            repo_id = repo["repo_id"]
            self.assertEqual(repo, expected[repo_id])


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
        for repo in config["RAW_TREES"]:
            sync_config = repo["importer_config"]
            sync_config["rsync_port"] = self.rsyncd.port
            sync_config["enabled"] = True
        self.site = site_config.SiteConfig(config)

    def _get_sync_config(self, **kwds):
        repo = self.site.get_repo_configs(**kwds)[0]
        params = repo["importer_config"].copy()
        local_path = self.local_path
        params["local_path"] = local_path
        return local_path, params

    def test_simple_tree(self):
        local_path, params = self._get_sync_config(mirrors=["simple_sync"])
        task = sync_trees.SyncTree(params)
        stats = dict(self.EXPECTED_TREE_STATS)
        self.check_sync_details(task.run_sync(), "SYNC_COMPLETED", stats)
        self.check_tree_layout(local_path)
        stats.update(self.EXPECTED_REPEAT_STATS)
        self.check_sync_details(task.run_sync(), "SYNC_UP_TO_DATE", stats)
        self.check_tree_layout(local_path)

    def test_versioned_tree(self):
        local_path, params = self._get_sync_config(mirrors=["versioned_sync"])
        task = sync_trees.SyncVersionedTree(params)
        stats = dict(self.EXPECTED_VERSIONED_STATS)
        self.check_sync_details(task.run_sync(), "SYNC_COMPLETED", stats)
        self.check_versioned_layout(local_path)
        stats.update(self.EXPECTED_REPEAT_STATS)
        self.check_sync_details(task.run_sync(), "SYNC_UP_TO_DATE", stats)
        self.check_versioned_layout(local_path)

    def test_snapshot_tree(self):
        local_path, params = self._get_sync_config(mirrors=["snapshot_sync"])
        details = self.setup_snapshot_layout(local_path)
        task = sync_trees.SyncSnapshotTree(params)
        stats = dict(self.EXPECTED_SNAPSHOT_STATS)
        self.check_sync_details(task.run_sync(), "SYNC_COMPLETED", stats)
        self.check_snapshot_layout(local_path, *details)
        # For an up-to-date tree, we transfer *nothing*
        for k in stats:
            stats[k] = 0
        self.check_sync_details(task.run_sync(), "SYNC_UP_TO_DATE", stats)
        self.check_snapshot_layout(local_path, *details)

    def test_raw_tree(self):
        local_path, params = self._get_sync_config(repos=["raw_sync"])
        task = sync_trees.SyncTree(params)
        stats = dict(self.EXPECTED_TREE_STATS)
        self.check_sync_details(task.run_sync(), "SYNC_COMPLETED", stats)
        self.check_tree_layout(local_path)
        stats.update(self.EXPECTED_REPEAT_STATS)
        self.check_sync_details(task.run_sync(), "SYNC_UP_TO_DATE", stats)
        self.check_tree_layout(local_path)

if __name__ == '__main__':
    unittest.main()
