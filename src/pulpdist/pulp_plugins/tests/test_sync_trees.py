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

import unittest
import shutil
import tempfile
import os.path

from .. import sync_trees
from . import rsync_daemon

_expected_files = [
    "data.txt",
    "data2.txt",
]

_unexpected_files = [
    "skip.txt",
]

_test_files = _expected_files + _unexpected_files

_expected_layout = [
    "",
    "subdir",
    "subdir/subdir",
    "subdir2",
]

_unexpected_dirs = [
    "subdir/irrelevant",
    "subdir/subdir/irrelevant",
    "subdir2/dull",
]

_source_layout = _expected_layout + _unexpected_dirs

_expected_versioned_trees = ["relevant-{}".format(i) for i in range(1, 5)]

_source_trees = [
    "simple",
    "versioned/ignored",
    "versioned/relevant-but-not-really",
]

_source_trees.extend(os.path.join("versioned", tree) for tree in _expected_versioned_trees)

_test_data_layout = [
    os.path.join(tree_dir, subdir)
        for tree_dir in _source_trees
            for subdir in _source_layout
]

_default_log = "/dev/null"

TEST_CASE_SYNC = dict(
    tree_name = "Simple Tree",
    remote_server = "localhost",
    remote_path = "/test_data/simple/",
    excluded_files = "*skip*".split(),
    sync_filters = "exclude_irrelevant/ exclude_dull/".split(),
    log_path = _default_log
)

TEST_CASE_VERSIONED_SYNC = dict(
    tree_name = "Versioned Tree",
    remote_server = "localhost",
    remote_path = "/test_data/versioned/",
    version_pattern = "relevant*",
    excluded_versions = "relevant-but*".split(),
    excluded_files = "*skip*".split(),
    sync_filters = "exclude_irrelevant/ exclude_dull/".split(),
    log_path = _default_log
)

TEST_CASE_SNAPSHOT_SYNC = dict(
    tree_name = "Snapshot Tree",
    remote_server = "localhost",
    remote_path = "/test_data/versioned/",
    version_pattern = "relevant*",
    excluded_versions = "relevant-but*".split(),
    excluded_files = "*skip*".split(),
    sync_filters = "exclude_irrelevant/ exclude_dull/".split(),
    log_path = _default_log
)

class TestSyncTree(unittest.TestCase):
    def setUp(self):
        self.rsyncd = rsyncd = rsync_daemon.RsyncDaemon(_test_data_layout, _test_files)
        rsyncd.start()
        self.local_path = local_path = tempfile.mkdtemp()
        self.params = dict(rsync_port = rsyncd.port,
                           local_path = local_path+'/')


    def tearDown(self):
        self.rsyncd.close()
        shutil.rmtree(self.local_path)

    def assertExists(self, full_path):
        err = "{} does not exist".format(full_path)
        # print ("Checking {} exists".format(full_path))
        self.assertTrue(os.path.exists(full_path), err)
        
    def assertNotExists(self, full_path):
        err = "{} exists".format(full_path)
        # print ("Checking {} does not exist".format(full_path))
        self.assertFalse(os.path.exists(full_path), err)

    def check_tree_layout(self, tree_path):
        for dname in _expected_layout:
            dpath = os.path.join(tree_path, dname)
            self.assertExists(dpath)
            for fname in _expected_files:
                fpath = os.path.join(dpath, fname)
                self.assertExists(fpath)
            for fname in _unexpected_files:
                fpath = os.path.join(dpath, fname)
                self.assertNotExists(fpath)
        for dname in _unexpected_dirs:
            dpath = os.path.join(tree_path, dname)
            self.assertNotExists(dpath)

    def check_tree_cross_links(self, tree_path_A, tree_path_B):
        trees = (tree_path_A, tree_path_B)
        for dname in _expected_layout:
            dpaths = [os.path.join(tree, dname) for tree in trees]
            map(self.assertExists, dpaths)
            for fname in _expected_files:
                fpaths = [os.path.join(dpath, fname) for dpath in dpaths]
                msg = "{} are different files".format(fpaths)
                self.assertTrue(os.path.samefile(*fpaths))

    def mark_trees_finished(self, base_path, trees):
        for tree in trees:
            status_path = os.path.join(base_path, tree, "STATUS")
            with open(status_path, 'w') as f:
                f.write("FINISHED\n")

    def test_sync(self):
        local_path = self.local_path
        params = self.params
        params.update(TEST_CASE_SYNC)
        task = sync_trees.SyncTree(**params)
        task.run_sync()
        self.check_tree_layout(local_path)

    def test_sync_versioned(self):
        local_path = self.local_path
        params = self.params
        params.update(TEST_CASE_VERSIONED_SYNC)
        task = sync_trees.SyncVersionedTree(**params)
        task.run_sync()
        for tree in _expected_versioned_trees:
            tree_path = os.path.join(local_path, tree)
            self.check_tree_layout(tree_path)

    def test_sync_snapshot(self):
        local_path = self.local_path
        params = self.params
        params.update(TEST_CASE_SNAPSHOT_SYNC)
        # Set up one local tree as already FINISHED
        skip_finished = _expected_versioned_trees[0]
        finished_path = os.path.join(local_path, skip_finished)
        os.makedirs(finished_path)
        self.mark_trees_finished(local_path, [skip_finished])
        # Set up all bar one remote tree as FINISHED
        rsyncd_path = self.rsyncd.tmp_dir + params["remote_path"]
        expect_sync = _expected_versioned_trees[1:-1]
        self.mark_trees_finished(rsyncd_path, [skip_finished] + expect_sync)
        # The last tree we expect to be skipped
        skip_not_ready = _expected_versioned_trees[-1]
        not_ready_path = os.path.join(local_path, skip_not_ready)
        # Run the sync task
        task = sync_trees.SyncSnapshotTree(**params)
        task.run_sync()
        # The tree locally marked as complete should not get updated
        self.assertExists(finished_path)
        self.assertEqual(os.listdir(finished_path), ["STATUS"])
        # The tree not remotely marked as complete should not get updated
        self.assertNotExists(not_ready_path)
        # The other trees should all get synchronised
        previous_tree_path = None
        for tree in expect_sync:
            tree_path = os.path.join(local_path, tree)
            self.check_tree_layout(tree_path)
            if previous_tree_path is not None:
                self.check_tree_cross_links(tree_path, previous_tree_path)
            previous_tree_path = tree_path
            status_path = os.path.join(tree_path, "STATUS")
            self.assertExists(status_path)
            with open(status_path) as f:
                self.assertEqual(f.read().strip(), "FINISHED")

    def test_sync_latest_link(self):
        local_path = self.local_path
        params = self.params
        params.update(TEST_CASE_SNAPSHOT_SYNC)
        link_name = "latest-relevant"
        link_path = os.path.join(local_path, link_name)
        params["latest_link_name"] = link_name
        # Set up all the remote trees as FINISHED
        rsyncd_path = self.rsyncd.tmp_dir + params["remote_path"]
        self.mark_trees_finished(rsyncd_path, _expected_versioned_trees)
        task = sync_trees.SyncSnapshotTree(**params)
        task.run_sync()
        # Symlink should exist and point to the last tree
        self.assertTrue(os.path.islink(link_path))
        expected_target = _expected_versioned_trees[-1]
        self.assertEqual(os.readlink(link_path), expected_target)


    def test_dir_protection(self):
        # We only test this with a simple sync
        # since versioned sync is merely a series
        # of simple syncs
        local_path = self.local_path
        params = self.params
        params.update(TEST_CASE_SYNC)
        task = sync_trees.SyncTree(**params)
        protected_path = os.path.join(local_path, "safe")
        protected_fname = os.path.join(protected_path, "PROTECTED")
        os.makedirs(protected_path)
        with open(protected_fname, 'w') as f:
            pass
        unprotected_path = os.path.join(local_path, "deleted")
        os.makedirs(unprotected_path)
        task.run_sync()
        self.check_tree_layout(local_path)
        self.assertExists(protected_path)
        self.assertExists(protected_fname)
        self.assertNotExists(unprotected_path)

    def test_file_consolidation(self):
        # We only test this with a simple sync
        # since the consolidation is handled by
        # the base class
        params = self.params
        params.update(TEST_CASE_SYNC)
        task = sync_trees.SyncTree(**params)
        rsyncd_path = self.rsyncd.tmp_dir + params["remote_path"]
        extra_path = os.path.join(rsyncd_path, "extra.txt")
        copied_path = os.path.join(rsyncd_path, "copied.txt")
        with open(extra_path, 'w') as f:
            f.write("Hello world!")
        shutil.copy2(extra_path, copied_path)
        self.assertFalse(os.path.samefile(extra_path, copied_path))
        task.run_sync()
        local_path = self.local_path
        extra_path = os.path.join(local_path, "extra.txt")
        copied_path = os.path.join(local_path, "copied.txt")
        self.assertTrue(os.path.samefile(extra_path, copied_path))


    # TODO: Verify copying of other symlinks
    # TODO: Delete old versioned directories


if __name__ == '__main__':
    unittest.main()
